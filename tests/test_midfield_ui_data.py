"""Simulator preparation uses fictional local JSON and unchanged backend validation."""

from copy import deepcopy
from dataclasses import replace

from football_scouting_lab import ui_data
from football_scouting_lab.metrics import MetricCounts
from football_scouting_lab.roles import EligibilityThresholds
from football_scouting_lab.team_fit import compare_midfield

BASELINE = ((3345, 2444), (224677, 2447), (289711, 2975))
CANDIDATE = (20475, 2444)


def test_fixed_pool_and_feature_rows_preserve_backend_results(midfield_data_dir):
    data = ui_data.load_scouting_data(str(midfield_data_dir))
    original = deepcopy(data)
    cohort, exclusions = ui_data.midfield_cohort(data, EligibilityThresholds())
    assert not exclusions
    assert len(cohort) == 4
    result = compare_midfield(cohort, BASELINE, 2, CANDIDATE)
    assert result.weighted_coverage_change == 25
    for row, feature in zip(
        ui_data.midfield_feature_rows(result), result.features, strict=True
    ):
        assert row["Before coverage"] == feature.before_coverage
        assert row["After coverage"] == feature.after_coverage
        assert row["Coverage change"] == feature.coverage_change
        assert row["Before raw mean"] == feature.before_mean
        assert row["After raw mean"] == feature.after_mean
        assert row["Weighted contribution (points)"] == feature.weighted_change
    assert data == original


def test_incomplete_missing_and_ineligible_demo_entries_are_reported(midfield_data_dir):
    data = ui_data.load_scouting_data(str(midfield_data_dir))
    players = tuple(
        replace(
            player, rated=MetricCounts(1, 1, defensive_duels_with_unknown_outcome=1)
        )
        if player.player_id == CANDIDATE[0]
        else player
        for player in data.metrics.players
        if player.player_id != 3345
    )
    data = replace(data, metrics=replace(data.metrics, players=players))
    cohort, exclusions = ui_data.midfield_cohort(data, EligibilityThresholds())
    assert len(cohort) == 2
    assert any(
        "successful_defensive_duels_per90" in row["Exclusion reason"]
        for row in exclusions
    )
    assert any(
        "absent from local metrics" in row["Exclusion reason"] for row in exclusions
    )
    empty, reasons = ui_data.midfield_cohort(data, EligibilityThresholds(10000, 1))
    assert empty == ()
    assert any(
        "below minimum rated minutes" in row["Exclusion reason"] for row in reasons
    )
