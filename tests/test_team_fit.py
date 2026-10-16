"""Fictional individual metrics; no source data or inferred football positions."""

from copy import deepcopy
from dataclasses import replace

import pytest

from football_scouting_lab.metrics import (
    MetricCounts,
    PlayerMatchMetrics,
    PlayerSeasonMetrics,
)
from football_scouting_lab.team_fit import (
    PROFILE_METRICS,
    compare_midfield,
    normalize_profile_weights,
)

BASELINE = ((1, 10), (2, 10), (3, 10))
CANDIDATE = (4, 10)


def sample(player_id, *, team=10, counts=None, minutes=900, rated_matches=10):
    counts = counts if counts is not None else MetricCounts(100, 90)
    matches = tuple(
        PlayerMatchMetrics(
            number,
            team,
            player_id,
            True,
            minutes / rated_matches
            if number <= rated_matches and rated_matches
            else None,
            10,
            MetricCounts(),
            ("synthetic timing approximation",),
        )
        for number in range(1, 11)
    )
    return PlayerSeasonMetrics(player_id, team, matches, counts, counts, minutes)


@pytest.fixture
def cohort():
    return [
        sample(1),
        sample(2, counts=MetricCounts(200, 160, 10, 30, 20)),
        sample(3, counts=MetricCounts(300, 210, 20, 30, 10)),
        sample(4, counts=MetricCounts(400, 240, 30, 30, 30)),
    ]


def compare(cohort, **kwargs):
    return compare_midfield(cohort, BASELINE, 0, CANDIDATE, **kwargs)


def test_feature_formulas_and_signed_summary(cohort):
    result = compare(cohort)
    passing, completion, interceptions, duels = result.features

    assert result.baseline_lineup == BASELINE
    assert result.replaced_id == (1, 10)
    assert result.candidate_id == CANDIDATE
    assert result.replacement_slot == 0
    assert result.updated_lineup == ((4, 10), (2, 10), (3, 10))
    assert passing.before_values == (10, 20, 30)
    assert passing.after_values == (40, 20, 30)
    assert passing.before_mean == 20
    assert passing.after_mean == 30
    assert passing.mean_change == 10
    assert completion.before_mean == 80
    assert (
        completion.after_mean == 70
    )  # average individual %, not pooled pass completion
    assert result.feature_ranges["pass_attempts_per90"] == (10, 40)
    assert passing.before_coverage == pytest.approx(2 / 3)
    assert passing.after_coverage == 1
    assert completion.coverage_change == pytest.approx(-1 / 3)
    assert interceptions.coverage_change == pytest.approx(1 / 3)
    assert duels.coverage_change == pytest.approx(1 / 3)
    assert result.weighted_coverage_change == pytest.approx(100 / 6)
    assert result.weighted_coverage_change == sum(
        feature.weighted_change for feature in result.features
    )
    assert result.before[0].player is cohort[0]
    assert result.after[0].player is cohort[3]
    assert any("four distinct" in warning for warning in result.warnings)
    assert any("not observed tactical positions" in note for note in result.limitations)


def test_weights_change_only_weighted_summary_not_feature_scales(cohort):
    passing = compare(cohort, weights={"pass_attempts_per90": 10})
    completion = compare(cohort, weights={"pass_completion_pct": 2})

    assert passing.weighted_coverage_change == pytest.approx(100 / 3)
    assert completion.weighted_coverage_change == pytest.approx(-100 / 3)
    assert passing.feature_ranges == completion.feature_ranges
    assert len(passing.features) == len(completion.features) == 4
    assert passing.features[1].weight == 0
    assert passing.features[1].weighted_change == 0
    assert passing.features[1].mean_change == -10
    assert sum(passing.weights.values()) == 1
    huge = normalize_profile_weights(dict.fromkeys(PROFILE_METRICS, 1e308))
    assert huge == dict.fromkeys(PROFILE_METRICS, 0.25)


def test_fixed_cohort_is_shared_across_lineups_and_candidates(cohort):
    extra = sample(5, counts=MetricCounts(1000, 500, 100, 100, 100))
    fixed = cohort + [extra]
    first = compare(fixed)
    second = compare_midfield(fixed, BASELINE, 0, (5, 10))

    assert first.comparison_cohort == second.comparison_cohort
    assert first.feature_ranges == second.feature_ranges
    assert first.feature_ranges["pass_attempts_per90"] == (10, 100)
    assert first.features[0].before_coverage == pytest.approx(2 / 9)
    assert first.features[0].after_coverage == pytest.approx(1 / 3)
    assert first.features[0].coverage_change == pytest.approx(1 / 9)


def test_constant_features_and_identical_profiles_are_explicit():
    cohort = [sample(number) for number in range(1, 5)]
    result = compare(cohort)

    assert result.weighted_coverage_change == 0
    assert all(
        feature.before_coverage == feature.after_coverage == 0.5
        for feature in result.features
    )
    assert all(
        feature.mean_change == feature.coverage_change == 0
        for feature in result.features
    )
    assert sum("constant feature" in warning for warning in result.warnings) == 4


@pytest.mark.parametrize("slot", [-1, 3, 1.0, True, "0", None])
def test_invalid_slot_is_rejected(cohort, slot):
    with pytest.raises(ValueError, match="replacement slot"):
        compare_midfield(cohort, BASELINE, slot, CANDIDATE)


@pytest.mark.parametrize(
    "baseline", [BASELINE[:2], BASELINE + ((5, 10),), ((1, 10), (1, 20), (3, 10))]
)
def test_baseline_requires_three_distinct_underlying_players(cohort, baseline):
    with pytest.raises(ValueError, match="three distinct underlying players"):
        compare_midfield(cohort, baseline, 0, CANDIDATE)


@pytest.mark.parametrize("candidate", [(1, 10), (1, 20), (2, 10), (3, 99)])
def test_candidate_already_in_lineup_is_rejected_across_teams(cohort, candidate):
    with pytest.raises(ValueError, match="candidate already present"):
        compare_midfield(cohort, BASELINE, 0, candidate)


@pytest.mark.parametrize("key", [(0, 10), (True, 10), (1, -10), (1,), [1, 10], "1/10"])
def test_invalid_identity(cohort, key):
    with pytest.raises(ValueError, match="positive player_id"):
        compare_midfield(cohort, BASELINE, 0, key)


def test_missing_and_duplicate_cohort_rows_are_not_silently_fixed(cohort):
    with pytest.raises(ValueError, match="duplicate player/team"):
        compare(cohort + [cohort[0]])
    with pytest.raises(ValueError, match="absent from fixed comparison cohort"):
        compare_midfield(cohort, ((1, 20), *BASELINE[1:]), 0, CANDIDATE)
    for size in range(4):
        with pytest.raises(ValueError, match="absent from fixed comparison cohort"):
            compare(cohort[:size])


@pytest.mark.parametrize("minutes", [None, 0, -1, float("inf"), float("nan"), True])
def test_missing_or_invalid_rated_minutes_fail(cohort, minutes):
    cohort[3] = replace(cohort[3], rated_minutes=minutes)
    with pytest.raises(ValueError, match="positive rated minutes"):
        compare(cohort)


@pytest.mark.parametrize(
    "counts,metric",
    [
        (MetricCounts(0, 0), "pass_completion_pct"),
        (MetricCounts(100, 90, passes_with_unknown_outcome=1), "pass_completion_pct"),
        (
            MetricCounts(100, 90, defensive_duels_with_unknown_outcome=1),
            "successful_defensive_duels_per90",
        ),
        (MetricCounts(100, 110), "pass_completion_pct"),
        (MetricCounts(100, 90, interceptions=-1), "interceptions_per90"),
    ],
)
def test_incomplete_invalid_metrics_fail_even_at_zero_weight(cohort, counts, metric):
    cohort[3] = replace(cohort[3], rated=counts)
    with pytest.raises(ValueError, match=metric):
        compare(cohort, weights={"pass_attempts_per90": 1})


def test_incomplete_unselected_cohort_member_is_not_silently_dropped(cohort):
    missing = replace(sample(5), rated=None)
    with pytest.raises(ValueError, match=r"\(5, 10\).*counts required"):
        compare(cohort + [missing])
    with pytest.raises(ValueError, match="rated recorded appearances"):
        compare(cohort + [replace(sample(5), matches=())])


@pytest.mark.parametrize(
    "weights",
    [
        {},
        {"bogus": 1},
        {"pass_attempts_per90": 0},
        {"pass_attempts_per90": -1},
        {"pass_attempts_per90": True},
        {"pass_attempts_per90": "1"},
        {"pass_attempts_per90": float("inf")},
        {"pass_attempts_per90": float("nan")},
    ],
)
def test_invalid_weights(cohort, weights):
    with pytest.raises(ValueError, match="weight|metric"):
        compare(cohort, weights=weights)


def test_transfers_preserve_ids_context_samples_and_determinism(cohort):
    transferred = replace(
        cohort[3],
        team_id=20,
        matches=tuple(replace(row, team_id=20) for row in cohort[3].matches),
    )
    cohort[3] = transferred
    cohort.append(sample(2, team=30))
    cohort[0] = sample(1, rated_matches=8)
    original = deepcopy(cohort)
    result = compare_midfield(cohort, BASELINE, 2, (4, 20))
    shuffled = compare_midfield(
        reversed(cohort),
        list(BASELINE),
        2,
        (4, 20),
        weights={metric: 10 for metric in reversed(PROFILE_METRICS)},
    )

    assert result == shuffled
    assert cohort == original
    assert result.updated_lineup == ((1, 10), (2, 10), (4, 20))
    assert result.before[0].rated_matches == 8
    assert result.before[0].recorded_appearances == 10
    assert result.before[0].appearance_coverage == 0.8
    assert result.before[0].player.matches[0].warnings == (
        "synthetic timing approximation",
    )
    assert any("historical team rows" in warning for warning in result.warnings)
    assert any(
        "incomplete appearance coverage" in warning for warning in result.warnings
    )
    assert {profile.player_team_id for profile in result.comparison_cohort} >= {
        (2, 10),
        (2, 30),
    }


def test_nonappearance_events_and_source_warnings_remain_visible(cohort):
    unrecorded = PlayerMatchMetrics(
        11,
        10,
        1,
        False,
        None,
        1,
        MetricCounts(1, 1),
        ("synthetic event without recorded appearance",),
    )
    cohort[0] = replace(cohort[0], matches=(*cohort[0].matches, unrecorded))
    result = compare(cohort)
    profile = result.before[0]
    assert profile.unrecorded_event_matches == 1
    assert profile.recorded_appearances == profile.rated_matches == 10
    assert profile.appearance_coverage == 1
    assert profile.player.matches[-1] is unrecorded
    assert any(
        "events without recorded appearances" in warning for warning in result.warnings
    )
