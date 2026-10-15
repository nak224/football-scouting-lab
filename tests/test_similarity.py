"""Explicitly synthetic metric profiles; no real player/event fixtures."""

from dataclasses import replace

import pytest

from football_scouting_lab.metrics import (
    MetricCounts,
    PlayerMatchMetrics,
    PlayerSeasonMetrics,
)
from football_scouting_lab.roles import EligibilityThresholds, PositionReview
from football_scouting_lab.similarity import (
    compare_styles,
    normalize_style_weights,
    replacement_shortlist,
)

REVIEW = PositionReview("included", "synthetic:review", "Fictional central midfielder")


def sample(player_id, *, team=10, counts=None, minutes=900, rated_matches=10):
    counts = counts if counts is not None else MetricCounts(100, 80, 20, 10, 5)
    matches = tuple(
        PlayerMatchMetrics(
            number,
            team,
            player_id,
            True,
            minutes / rated_matches if number <= rated_matches else None,
            0,
            MetricCounts(),
            ("synthetic timing uncertainty",),
        )
        for number in range(1, 11)
    )
    return PlayerSeasonMetrics(player_id, team, matches, counts, counts, minutes)


def compare(players, reference=(1, 10), *, reviews=None, **kwargs):
    reviews = (
        {(p.player_id, p.team_id): REVIEW for p in players}
        if reviews is None
        else reviews
    )
    return compare_styles(players, reviews, reference, **kwargs)


def row(result, key):
    return next(r for r in result.candidates if r.candidate_id == key)


def test_identical_profiles_have_zero_distance_even_in_a_varying_cohort():
    result = compare(
        [sample(1), sample(2), sample(3, counts=MetricCounts(200, 180, 40, 20, 15))]
    )
    identical = row(result, (2, 10))

    assert identical.reference_id == (1, 10)
    assert identical.score == 100
    assert identical.distance == 0
    assert all(
        d.normalized_difference == d.contribution == 0 for d in identical.differences
    )
    assert result.reference.player.rated_minutes == 900
    assert identical.candidate.rated_matches == 10
    assert identical.candidate.appearance_coverage == 1
    assert identical.candidate.player.matches[0].warnings == (
        "synthetic timing uncertainty",
    )


def test_opposite_profiles_have_bounded_score_and_explainable_weighted_distance():
    result = compare([sample(1), sample(2, counts=MetricCounts(200, 180, 0, 10, 0))])
    opposite = row(result, (2, 10))

    assert opposite.score == 0
    assert opposite.distance == 1
    assert sum(d.contribution for d in opposite.differences) == 1
    assert all(d.contribution == 0.25 for d in opposite.differences)
    passing = next(d for d in opposite.differences if d.metric == "pass_attempts_per90")
    assert (
        passing.reference_value,
        passing.candidate_value,
        passing.raw_difference,
    ) == (10, 20, 10)
    assert (passing.reference_normalized, passing.candidate_normalized) == (0, 1)
    assert result.feature_ranges["pass_attempts_per90"] == (10, 20)
    assert replacement_shortlist(result) == (opposite,)  # Score zero is not missing.


def test_minmax_distance_preserves_relative_gaps_not_just_ordinal_rank():
    result = compare(
        [
            sample(1),
            sample(2, counts=MetricCounts(110, 88)),
            sample(3, counts=MetricCounts(200, 160)),
        ],
        weights={"pass_attempts_per90": 1},
    )

    assert row(result, (2, 10)).score == pytest.approx(90)
    assert row(result, (2, 10)).distance == pytest.approx(0.1)


def test_weight_changes_change_style_shortlist_and_do_not_mutate_input():
    players = [
        sample(1),
        sample(2, counts=MetricCounts(100, 80, 0, 10, 5)),
        sample(3, counts=MetricCounts(200, 160, 20, 10, 5)),
    ]
    weights = {"pass_attempts_per90": 8}
    passing = compare(players, weights=weights)
    defensive = compare(players, weights={"interceptions_per90": 3})

    assert replacement_shortlist(passing)[0].candidate_id == (2, 10)
    assert replacement_shortlist(defensive)[0].candidate_id == (3, 10)
    assert weights == {"pass_attempts_per90": 8}
    assert passing.weights == {"pass_attempts_per90": 1}


def test_constant_features_contribute_zero_without_redistributing_their_weights():
    result = compare([sample(1), sample(2, counts=MetricCounts(200, 160, 20, 10, 5))])
    other = row(result, (2, 10))

    assert other.score == 75  # Only passing involvement varies; others stay constant.
    assert len(other.differences) == 4
    assert sum(d.weight for d in other.differences) == 1
    constants = [d for d in other.differences if d.metric != "pass_attempts_per90"]
    assert all(
        d.reference_normalized == d.candidate_normalized == 0.5 for d in constants
    )
    assert all(d.contribution == 0 for d in constants)
    assert any("constant features" in w for w in result.warnings)


@pytest.mark.parametrize("players", [[sample(1)], [sample(1), sample(2)]])
def test_tiny_and_constant_cohorts_are_explicitly_uninformative(players):
    result = compare(players)

    assert all(r.score == 100 for r in result.candidates)
    assert any("tiny normalization cohort" in w for w in result.warnings)
    assert any("100 is uninformative" in w for w in result.warnings)
    assert len(replacement_shortlist(result)) == len(players) - 1


def test_missing_candidate_measurements_are_not_scored_or_used_for_scaling():
    missing = sample(
        3, counts=MetricCounts(100000, 80000, passes_with_unknown_outcome=1)
    )
    result = compare([sample(1), sample(2), missing])
    excluded = row(result, (3, 10))

    assert result.normalization_ids == ((1, 10), (2, 10))
    assert excluded.score is None and excluded.distance is None
    assert excluded.measurements["pass_completion_pct"] is None
    assert excluded.differences == ()
    assert (
        "unavailable or invalid style metric: pass_completion_pct" in excluded.reasons
    )
    assert [r.candidate_id for r in replacement_shortlist(result)] == [(2, 10)]


def test_disabled_missing_metric_is_not_silently_imputed():
    player = sample(2, counts=MetricCounts(100, 80, passes_with_unknown_outcome=1))
    result = compare(
        [sample(1), player],
        weights={"pass_attempts_per90": 1, "pass_completion_pct": 0},
    )

    assert row(result, (2, 10)).score == 100
    assert row(result, (2, 10)).measurements["pass_completion_pct"] is None
    assert len(row(result, (2, 10)).differences) == 1
    assert result.weights["pass_completion_pct"] == 0


def test_missing_rated_counts_never_become_zero_style_values():
    result = compare([sample(1), replace(sample(2), rated=None)])

    assert row(result, (2, 10)).score is None
    assert all(v is None for v in row(result, (2, 10)).measurements.values())


def test_unknown_defensive_outcomes_are_not_treated_as_zero_wins():
    result = compare(
        [sample(1), sample(2, counts=MetricCounts(100, 80, 20, 10, 5, 0, 1))]
    )

    assert row(result, (2, 10)).score is None
    assert row(result, (2, 10)).measurements["successful_defensive_duels_per90"] is None


@pytest.mark.parametrize(
    "player,reason",
    [
        (sample(1, minutes=599), "below minimum rated minutes"),
        (sample(1, rated_matches=5), "below minimum appearance coverage"),
        (replace(sample(1), rated_minutes=None), "positive rated minutes unavailable"),
        (sample(1, counts=MetricCounts()), "unavailable or invalid style metric"),
        (
            sample(1, counts=MetricCounts(100, 80, 20, 10, 5, 0, 1)),
            "unavailable or invalid style metric",
        ),
    ],
)
def test_ineligible_or_incomplete_reference_fails_explicitly(player, reason):
    with pytest.raises(ValueError, match=reason):
        compare([player, sample(2)])


def test_position_reviews_are_reused_without_inference_for_reference_or_candidate():
    with pytest.raises(ValueError, match="position review: unverified"):
        compare([sample(1), sample(2)], reviews={})
    result = compare([sample(1), sample(2)], reviews={(1, 10): REVIEW})

    assert row(result, (2, 10)).score is None
    assert "position review: unverified" in row(result, (2, 10)).reasons
    assert replacement_shortlist(result) == ()


def test_minimum_thresholds_are_configurable_and_retained():
    thresholds = EligibilityThresholds(300, 0.4)
    result = compare(
        [sample(1), sample(2, minutes=450, rated_matches=5)], thresholds=thresholds
    )

    assert result.thresholds == thresholds
    assert row(result, (2, 10)).score is not None
    assert row(result, (2, 10)).candidate.appearance_coverage == 0.5


def test_ineligible_outliers_do_not_distort_cohort_ranges():
    result = compare(
        [
            sample(1),
            sample(2, counts=MetricCounts(200, 160)),
            sample(3, minutes=599, counts=MetricCounts(100000, 80000)),
        ],
        weights={"pass_attempts_per90": 1},
    )

    assert result.normalization_ids == ((1, 10), (2, 10))
    assert result.feature_ranges["pass_attempts_per90"] == (10, 20)
    assert row(result, (2, 10)).score == 0


def test_reference_player_is_excluded_across_all_transfer_teams_before_limiting():
    result = compare([sample(1), sample(1, team=20), sample(2)])

    assert row(result, (1, 20)).score == 100  # Pair comparison remains valid.
    assert [r.candidate_id for r in replacement_shortlist(result, limit=1)] == [(2, 10)]
    only_self = compare([sample(1), sample(1, team=20)])
    assert replacement_shortlist(only_self) == ()
    assert any("no eligible replacement" in w for w in only_self.warnings)


def test_ties_and_other_players_transfer_rows_have_stable_id_order():
    players = [sample(3), sample(2, team=20), sample(1), sample(2, team=10)]
    first = compare(players)
    second = compare(list(reversed(players)))

    assert first == second
    assert [r.candidate_id for r in replacement_shortlist(first)] == [
        (2, 10),
        (2, 20),
        (3, 10),
    ]


def test_pairwise_distance_is_symmetric_in_the_same_cohort():
    players = [
        sample(1),
        sample(2, counts=MetricCounts(150, 135, 30, 20, 10)),
        sample(3),
    ]
    first = row(compare(players), (2, 10))
    second = row(compare(players, reference=(2, 10)), (1, 10))

    assert first.distance == second.distance
    assert first.score == second.score
    assert [d.raw_difference for d in first.differences] == [
        -d.raw_difference for d in second.differences
    ]


@pytest.mark.parametrize(
    "weights",
    [
        {},
        {"pass_attempts_per90": 0},
        {"pass_attempts_per90": -1},
        {"pass_attempts_per90": True},
        {"pass_attempts_per90": "1"},
        {"pass_attempts_per90": float("nan")},
        {"pass_attempts_per90": float("inf")},
        {"progressive_passes_per90": 1},
        {"accurate_passes_per90": 1},
        {"pass_attempts_per90": 10**1000},
    ],
)
def test_invalid_weights_fail_instead_of_producing_scores(weights):
    with pytest.raises(ValueError):
        compare([sample(1), sample(2)], weights=weights)


def test_weight_normalization_supports_large_values_and_insertion_order():
    first = normalize_style_weights(
        {"pass_attempts_per90": 1e308, "interceptions_per90": 1e308}
    )
    second = normalize_style_weights(
        {"interceptions_per90": 1, "pass_attempts_per90": 1}
    )

    assert first == second == {"interceptions_per90": 0.5, "pass_attempts_per90": 0.5}


@pytest.mark.parametrize(
    "reference", [(999, 10), (1, 20), (True, 10), (1,), [1, 10], (0, 10)]
)
def test_missing_or_invalid_reference_ids_fail_explicitly(reference):
    with pytest.raises(ValueError, match="reference"):
        compare([sample(1)], reference=reference)


def test_empty_input_cannot_fabricate_a_reference():
    with pytest.raises(ValueError, match="absent"):
        compare([])


@pytest.mark.parametrize("limit", [-1, True, 1.5, "2"])
def test_invalid_shortlist_limits_are_rejected(limit):
    with pytest.raises(ValueError, match="shortlist limit"):
        replacement_shortlist(compare([sample(1), sample(2)]), limit=limit)


def test_empty_and_limited_shortlists_keep_comparison_context_unchanged():
    result = compare([sample(1), sample(2), sample(3)])

    assert replacement_shortlist(result, limit=0) == ()
    assert len(replacement_shortlist(result, limit=1)) == 1
    assert len(replacement_shortlist(result, limit=99)) == 2
    assert len(result.candidates) == 3


def test_style_similarity_does_not_call_role_scoring(monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError("style similarity must not consume role fit")

    monkeypatch.setattr("football_scouting_lab.roles.score_role", forbidden)

    assert row(compare([sample(1), sample(2)]), (2, 10)).score == 100
