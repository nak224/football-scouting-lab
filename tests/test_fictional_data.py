"""Portfolio demo generation, provenance separation and real pipeline behavior."""

import json

import pytest

from football_scouting_lab.demo_cohort import DEMO_REVIEWS
from football_scouting_lab.fictional_data import (
    BASELINE,
    CANDIDATE,
    REVIEWS,
    write_fictional_data,
)
from football_scouting_lab.recruitment import rank_replacements
from football_scouting_lab.roles import EligibilityThresholds
from football_scouting_lab.team_fit import compare_midfield
from football_scouting_lab.ui_data import (
    DATA_FILES,
    explorer_rows,
    load_fictional_demo,
    load_scouting_data,
    midfield_cohort,
    present_reviews,
)


def test_demo_is_deterministic_separate_and_uses_all_existing_analytics(tmp_path):
    first = write_fictional_data(tmp_path / "first")
    second = write_fictional_data(tmp_path / "second")
    assert all(
        (first / name).read_bytes() == (second / name).read_bytes()
        for name in DATA_FILES
    )
    data = load_scouting_data(str(first))
    assert data == load_fictional_demo()
    assert data.fictional
    assert len(data.metrics.matches) == 14
    assert len(data.metrics.players) == 4
    assert len(DEMO_REVIEWS) == 4
    assert set(REVIEWS).isdisjoint(DEMO_REVIEWS)
    assert set(present_reviews(data)) == set(REVIEWS)
    assert all(
        "FICTIONAL" in name
        for name in (*data.player_names.values(), *data.team_names.values())
    )
    assert {row["Position review"] for row in explorer_rows(data)} == {
        "Fictional demo midfielder"
    }
    pool, exclusions = midfield_cohort(data, EligibilityThresholds())
    assert len(pool) == 4 and not exclusions
    assert all(player.rated_minutes >= 600 for player in pool)
    for role in ("deep_lying_playmaker", "ball_winning_midfielder"):
        ranking = rank_replacements(
            data.metrics.players, present_reviews(data), BASELINE[1], role
        )
        assert len(ranking.shortlist) == 3
        assert all(row.combined_score is not None for row in ranking.shortlist)
    result = compare_midfield(pool, BASELINE, 2, CANDIDATE)
    assert len(result.features) == 4
    assert all(profile.appearance_coverage == 1 for profile in result.comparison_cohort)


def test_existing_data_is_never_overwritten(tmp_path):
    existing = tmp_path / "teams.json"
    existing.write_text("KEEP EXISTING DATA")
    with pytest.raises(FileExistsError, match="existing dataset files"):
        write_fictional_data(tmp_path)
    assert existing.read_text() == "KEEP EXISTING DATA"
    assert not (tmp_path / "players.json").exists()


def test_raw_event_changes_change_calculated_metrics(tmp_path):
    root = write_fictional_data(tmp_path)
    before = load_scouting_data(str(root))
    path = root / "events_Germany.json"
    events = json.loads(path.read_text())
    event = next(
        row
        for row in events
        if row["playerId"] == BASELINE[0][0] and row["eventId"] == 8
    )
    event["tags"] = [{"id": 1802}]
    path.write_text(json.dumps(events))
    after = load_scouting_data(str(root))
    original = next(
        player
        for player in before.metrics.players
        if player.player_id == BASELINE[0][0]
    )
    changed = next(
        player for player in after.metrics.players if player.player_id == BASELINE[0][0]
    )
    assert changed.rated.accurate_passes == original.rated.accurate_passes - 1
    assert changed.rated.pass_completion_pct < original.rated.pass_completion_pct


def test_marked_fictional_and_unmarked_data_cannot_be_mixed(tmp_path):
    root = write_fictional_data(tmp_path)
    path = root / "matches_Germany.json"
    matches = json.loads(path.read_text())
    matches[0].pop("fictionalDemo")
    path.write_text(json.dumps(matches))
    with pytest.raises(ValueError, match="cannot be mixed"):
        load_scouting_data(str(root))


@pytest.mark.parametrize("marker", ["fictional-v999", "", None, True, 1, {}, []])
@pytest.mark.parametrize("all_matches", [True, False])
def test_unknown_or_inconsistent_versions_never_become_real_data(
    tmp_path, monkeypatch, marker, all_matches
):
    from football_scouting_lab import ui_data

    root = write_fictional_data(tmp_path)
    path = root / "matches_Germany.json"
    matches = json.loads(path.read_text())
    for match in matches if all_matches else matches[:1]:
        match["fictionalDemo"] = marker
    path.write_text(json.dumps(matches))

    def unexpected_event_load(*args):
        pytest.fail("Rejected provenance markers must be checked before loading events")

    monkeypatch.setattr(ui_data, "load_events", unexpected_event_load)
    with pytest.raises(ValueError, match="Unknown or invalid fictionalDemo version"):
        load_scouting_data(str(root))
