"""External review configuration: all decisions and source records are synthetic."""

import json
from dataclasses import replace

import pytest

from football_scouting_lab.cohort_reviews import load_position_reviews
from football_scouting_lab.roles import EligibilityThresholds, assess_eligibility
from football_scouting_lab.ui_data import (
    apply_review_file,
    configured_reviews,
    load_fictional_demo,
    load_scouting_data,
    midfield_cohort,
    present_reviews,
    reference_options,
    review_key,
    review_rows,
)


def decision(player=101, team=201, status="included", **changes):
    return {
        "player_id": player,
        "team_id": team,
        "status": status,
        "evidence": "synthetic:review-only",
        "note": "Fictional decision for testing, not a real position review.",
        **changes,
    }


def write_reviews(path, records):
    path.write_text(json.dumps(records), encoding="utf-8")
    return str(path)


def test_transfer_decisions_are_separate_and_do_not_mutate_cached_data(
    ui_data_dir, tmp_path, ui_demo_reviews
):
    data = load_scouting_data(str(ui_data_dir))
    path = write_reviews(
        tmp_path / "reviews.json",
        [decision(), decision(101, 202, "excluded"), decision(104, 202)],
    )
    custom = apply_review_file(data, path)
    assert custom.metrics is data.metrics  # no event/metric recalculation or copy
    assert custom.custom_reviews is not None and data.custom_reviews is None
    assert configured_reviews(data) == ui_demo_reviews
    assert apply_review_file(data, "  ") is data
    assert configured_reviews(apply_review_file(custom, "")) == ui_demo_reviews
    eligibility = assess_eligibility(
        custom.metrics.players, present_reviews(custom), EligibilityThresholds(0, 0)
    )
    rows = {(row.player.player_id, row.player.team_id): row for row in eligibility}
    assert rows[101, 201].eligible
    assert rows[101, 202].reasons == ("position review: excluded",)
    assert rows[102, 201].review.status == "unverified"
    assert reference_options(custom, EligibilityThresholds(0, 0), None) == (
        (101, 201),
        (104, 202),
    )
    # Review content, including revised evidence at the same path, identifies config.
    before = review_key(custom)
    write_reviews(
        tmp_path / "reviews.json", [decision(evidence="synthetic:revision-2")]
    )
    revised = apply_review_file(data, path)
    assert review_key(revised) != before
    assert configured_reviews(revised)[101, 201].evidence == "synthetic:revision-2"
    assert configured_reviews(custom)[101, 201].evidence == "synthetic:review-only"


def test_match_sheet_bench_is_known_but_has_no_metric_sample(ui_data_dir, tmp_path):
    data = load_scouting_data(str(ui_data_dir))
    assert (109, 201) in data.historical_pairs
    assert (101, 9999) not in data.historical_pairs  # currentTeamId is irrelevant
    path = write_reviews(tmp_path / "reviews.json", [decision(109, 201)])
    custom = apply_review_file(data, path)
    assert present_reviews(custom) == {}
    assert review_rows(custom)[0]["Metric sample"] == "No player/team metric sample"
    cohort, exclusions = midfield_cohort(custom, EligibilityThresholds(0, 0))
    assert not cohort
    assert "absent from local metrics" in exclusions[0]["Exclusion reason"]


def test_empty_review_file_is_not_default_and_fake_cannot_receive_real_reviews(
    ui_data_dir, tmp_path
):
    path = write_reviews(tmp_path / "reviews.json", [])
    custom = apply_review_file(load_scouting_data(str(ui_data_dir)), path)
    assert configured_reviews(custom) == {}
    assert reference_options(custom, EligibilityThresholds(0, 0), None) == ()
    assert midfield_cohort(custom, EligibilityThresholds(0, 0)) == ((), [])
    fictional = load_fictional_demo()
    with pytest.raises(ValueError, match="cannot be applied to FICTIONAL"):
        apply_review_file(fictional, str(tmp_path / "does-not-exist.json"))
    assert configured_reviews(
        replace(fictional, custom_reviews={})
    ) == configured_reviews(fictional)


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (None, "exactly these fields"),
        ({}, "exactly these fields"),
        (decision(extra="unknown"), "exactly these fields"),
        (decision(player=True), "positive integer"),
        (decision(player="101"), "positive integer"),
        (decision(player=101.0), "positive integer"),
        (decision(team=0), "positive integer"),
        (decision(team=-1), "positive integer"),
        (decision(player=None), "positive integer"),
        (decision(player=999), "unknown historical"),
        (decision(team=202), "unknown historical"),
        (decision(status="unverified"), "status must"),
        (decision(status=None), "status must"),
        (decision(evidence="  "), "requires evidence"),
        (decision(status="excluded", evidence=""), "requires evidence"),
        (decision(note=""), "requires evidence"),
        (decision(evidence=7), "must be strings"),
        (decision(note=None), "must be strings"),
    ],
)
def test_invalid_decisions(tmp_path, record, message):
    path = write_reviews(tmp_path / "reviews.json", [record])
    with pytest.raises(ValueError, match=message):
        load_position_reviews(path, frozenset({(101, 201)}))


@pytest.mark.parametrize(
    ("content", "message"),
    [
        ("not JSON", "cannot read review JSON"),
        ('{"reviews": []}', "expected a JSON array"),
        ('[{"player_id": 101, "player_id": 102}]', "duplicate JSON key"),
        (
            json.dumps([decision(), decision(status="excluded")]),
            "duplicate player/team",
        ),
    ],
)
def test_invalid_files(tmp_path, content, message):
    path = tmp_path / "reviews.json"
    path.write_text(content)
    with pytest.raises(ValueError, match=message):
        load_position_reviews(path, frozenset({(101, 201)}))


def test_missing_review_file_is_a_configuration_error(tmp_path):
    with pytest.raises(ValueError, match="cannot read review JSON"):
        load_position_reviews(tmp_path / "missing.json", frozenset())


@pytest.mark.parametrize(
    "player,team,has_sample", [(109, 201, False), (101, 201, True)]
)
def test_match_sheet_pair_remains_valid_when_global_player_metadata_is_missing(
    ui_data_dir, tmp_path, player, team, has_sample
):
    players_path = ui_data_dir / "players.json"
    players = json.loads(players_path.read_text())
    players_path.write_text(
        json.dumps([row for row in players if row["wyId"] != player])
    )
    data = load_scouting_data(str(ui_data_dir))
    path = write_reviews(tmp_path / "reviews.json", [decision(player, team)])
    custom = apply_review_file(data, path)
    assert (player, team) in custom.historical_pairs
    assert custom.player_names[player] == f"Player {player}"
    assert review_rows(custom)[0]["Player metadata"] == "Missing from players.json"
    assert bool(present_reviews(custom)) == has_sample
    if has_sample:
        assert reference_options(custom, EligibilityThresholds(0, 0), None) == (
            (player, team),
        )
        sample = next(
            row
            for row in custom.metrics.players
            if (row.player_id, row.team_id) == (player, team)
        )
        assert all(
            "player ID missing from players.json" in row.warnings
            for row in sample.matches
        )
    else:
        assert reference_options(custom, EligibilityThresholds(0, 0), None) == ()
        cohort, exclusions = midfield_cohort(custom, EligibilityThresholds(0, 0))
        assert not cohort
        assert "absent from local metrics" in exclusions[0]["Exclusion reason"]
        assert "missing from players.json" in exclusions[0]["Exclusion reason"]
    # Actual absence from historical match sheets still fails, even for known IDs.
    write_reviews(tmp_path / "reviews.json", [decision(777, 201)])
    with pytest.raises(ValueError, match="unknown historical player/team"):
        apply_review_file(data, path)
