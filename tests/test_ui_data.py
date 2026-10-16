"""Presentation tests use only synthetic records and fictional review decisions."""

from dataclasses import replace

import pytest

from football_scouting_lab.demo_cohort import DEMO_REVIEWS
from football_scouting_lab.recruitment import rank_replacements
from football_scouting_lab.roles import EligibilityThresholds
from football_scouting_lab.ui_data import (
    dataset_key,
    display_text,
    explorer_rows,
    load_scouting_data,
    reference_options,
    shortlist_rows,
)


def test_shared_demo_cohort_unchanged():
    assert set(DEMO_REVIEWS) == {
        (3345, 2444),
        (20475, 2444),
        (224677, 2447),
        (289711, 2975),
    }


def test_cache_key_validates_files_and_detects_changes(ui_data_dir):
    root, stamps = dataset_key(str(ui_data_dir))
    assert root == str(ui_data_dir.resolve())
    assert len(stamps) == 4
    path = ui_data_dir / "teams.json"
    path.write_text(path.read_text() + "\n")
    assert dataset_key(root) != (root, stamps)
    path.unlink()
    with pytest.raises(ValueError, match="Missing data file.*teams.json"):
        dataset_key(root)
    with pytest.raises(ValueError, match="Enter the local directory"):
        dataset_key("   ")


def test_names_and_historical_rows_are_preserved(ui_data_dir, ui_demo_reviews):
    data = load_scouting_data(str(ui_data_dir))
    rows = explorer_rows(data)
    transfer = [row for row in rows if row["Player ID"] == 101]
    assert {row["Team ID"] for row in transfer} == {201, 202}
    assert all(row["Rated minutes"] == 96 for row in transfer)
    assert all(row["Coverage %"] == 100 for row in transfer)
    assert all(row["Position review"] == "Reviewed demo midfielder" for row in transfer)
    assert all(row["Historical team"] != "9999" for row in rows)
    unverified = next(row for row in rows if row["Player ID"] == 102)
    assert unverified["Position review"] == "Unverified position"
    assert unverified["Pass completion %"] is None
    assert 109 not in {row["Player ID"] for row in rows}  # unused substitute
    rows[0]["Player"] = "Changed display only"
    assert explorer_rows(data)[0]["Player"] != "Changed display only"
    assert display_text(r"J\\u00f6rg Müller") == "Jörg Müller"
    assert data.label((999, 888)) == "Player 999 · Team 888 (999/888)"


def test_unknown_metrics_stay_unknown(ui_data_dir):
    data = load_scouting_data(str(ui_data_dir))
    player = replace(data.metrics.players[0], rated=None, rated_minutes=None)
    data = replace(data, metrics=replace(data.metrics, players=(player,)))
    row = explorer_rows(data)[0]
    assert row["Rated minutes"] is None
    assert row["Pass attempts (rated)"] is None
    assert row["Pass attempts /90"] is None
    assert row["Accurate passes /90"] is None


def test_reference_options_reuse_style_validation(ui_data_dir, ui_demo_reviews):
    data = load_scouting_data(str(ui_data_dir))
    assert reference_options(data, EligibilityThresholds(), None) == ()
    thresholds = EligibilityThresholds(0, 0)
    assert reference_options(data, thresholds, None) == (
        (101, 201),
        (101, 202),
        (104, 202),
    )
    broken = tuple(replace(player, rated=None) for player in data.metrics.players)
    assert (
        reference_options(
            replace(data, metrics=replace(data.metrics, players=broken)),
            thresholds,
            None,
        )
        == ()
    )
    with pytest.raises(ValueError, match="positive"):
        reference_options(data, thresholds, {"pass_attempts_per90": 0})


def test_shortlist_keeps_source_scores_samples_and_transfer_identity(
    ui_data_dir, ui_demo_reviews
):
    data = load_scouting_data(str(ui_data_dir))
    result = rank_replacements(
        data.metrics.players,
        ui_demo_reviews,
        (101, 201),
        "deep_lying_playmaker",
        thresholds=EligibilityThresholds(0, 0),
    )
    (row,) = shortlist_rows(data, result)
    (original,) = result.shortlist
    assert (row["Player ID"], row["Team ID"]) == (104, 202)
    assert row["Combined score"] == original.combined_score
    assert row["Style similarity"] == original.style.score
    assert row["Role fit"] == original.role.score
    assert row["Rated matches"] == 2
    assert row["Coverage %"] == 100
    assert shortlist_rows(data, replace(result, shortlist=())) == []
