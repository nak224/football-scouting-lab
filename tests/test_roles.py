"""Synthetic metric samples and explicit fictional position-review decisions."""

from dataclasses import replace

import pytest

from football_scouting_lab.metrics import (
    MetricCounts,
    PlayerMatchMetrics,
    PlayerSeasonMetrics,
)
from football_scouting_lab.roles import (
    EligibilityThresholds,
    PositionReview,
    assess_eligibility,
    normalize_weights,
    score_role,
)

DLP = "deep_lying_playmaker"
BWM = "ball_winning_midfielder"
REVIEW = PositionReview("included", "synthetic:review", "Fictional central midfielder")


def sample(player_id, *, team=10, rated=10, appearances=10, minutes=900, counts=None):
    """Hand-built season sample; absent timing remains None in match rows."""
    counts = counts if counts is not None else MetricCounts(100, 80, 20, 10, 5)
    matches = tuple(
        PlayerMatchMetrics(
            number,
            team,
            player_id,
            True,
            minutes / rated if number <= rated and rated else None,
            0,
            MetricCounts(),
            ("synthetic timing warning",),
        )
        for number in range(1, appearances + 1)
    )
    return PlayerSeasonMetrics(player_id, team, matches, counts, counts, minutes)


def rank(players, role=DLP, *, weights=None, reviews=None, thresholds=None):
    if reviews is None:
        reviews = {(p.player_id, p.team_id): REVIEW for p in players}
    return score_role(
        players,
        reviews,
        role,
        weights=weights,
        thresholds=thresholds or EligibilityThresholds(),
    )


def test_broad_position_is_not_inferred_without_explicit_review():
    candidate = assess_eligibility([sample(1)], {})[0]

    assert candidate.review.status == "unverified"
    assert not candidate.eligible
    assert candidate.reasons == ("position review: unverified",)
    assert rank([sample(1)], reviews={}).candidates[0].score is None


def test_eligibility_thresholds_and_visible_sample_sizes():
    candidate = rank([sample(1, rated=6, minutes=600)]).candidates[0].eligibility

    assert candidate.eligible
    assert candidate.rated_matches == 6
    assert candidate.recorded_appearances == 10
    assert candidate.appearance_coverage == 0.6
    assert candidate.player.rated_minutes == 600
    assert candidate.player.matches[0].warnings == ("synthetic timing warning",)


@pytest.mark.parametrize(
    ("player", "reason"),
    [
        (sample(1, minutes=599), "below minimum rated minutes"),
        (sample(1, rated=5), "below minimum appearance coverage"),
        (sample(1, minutes=0), "positive rated minutes unavailable"),
        (replace(sample(1), rated_minutes=None), "positive rated minutes unavailable"),
        (sample(1, rated=0, appearances=0), "no recorded appearances"),
    ],
)
def test_ineligible_samples_are_reported_and_not_scored(player, reason):
    result = rank([player])

    assert result.reference_ids == ()
    assert result.candidates[0].score is None
    assert result.candidates[0].contributions == ()
    assert reason in result.candidates[0].reasons


def test_configurable_thresholds_do_not_bypass_positive_minutes_requirement():
    thresholds = EligibilityThresholds(0, 0)

    assert rank(
        [sample(1, minutes=1, rated=1)], thresholds=thresholds
    ).reference_ids == ((1, 10),)
    assert not rank([sample(1, minutes=0)], thresholds=thresholds).reference_ids


def test_review_is_scoped_to_historical_team_and_exclusion_is_explicit():
    result = rank(
        [sample(1, team=20), sample(1, team=10), sample(2)],
        reviews={
            (1, 10): REVIEW,
            (2, 10): PositionReview(
                "excluded", "synthetic:review", "Fictional wide player"
            ),
        },
    )

    assert result.reference_ids == ((1, 10),)
    assert result.candidates[0].eligibility.player.team_id == 10
    excluded = result.candidates[1:]
    assert [r.score for r in excluded] == [None, None]
    assert any("unverified" in reason for reason in excluded[0].reasons)
    assert any("excluded" in reason for reason in excluded[1].reasons)


def test_small_and_constant_cohorts_are_neutral_and_ties_use_original_ids():
    for players in ([sample(3)], [sample(3), sample(2), sample(1)]):
        result = rank(players)
        assert [r.score for r in result.candidates] == pytest.approx(
            [50] * len(players)
        )
        assert all(
            c.percentile == 50 for r in result.candidates for c in r.contributions
        )
        assert [r.eligibility.player.player_id for r in result.candidates] == sorted(
            p.player_id for p in players
        )


def test_weight_changes_explain_ranking_without_mutating_defaults():
    volume = sample(1, counts=MetricCounts(100, 50))
    completion = sample(2, counts=MetricCounts(50, 50))
    baseline = normalize_weights(DLP)
    result = rank([volume, completion], weights={"pass_attempts_per90": 2})
    opposite = rank([volume, completion], weights={"pass_completion_pct": 7})

    assert result.candidates[0].eligibility.player.player_id == 1
    assert opposite.candidates[0].eligibility.player.player_id == 2
    assert result.candidates[0].score == 100
    assert opposite.candidates[0].score == 100
    assert normalize_weights(DLP) == baseline
    explanation = result.candidates[0].contributions[0]
    assert explanation.metric == "pass_attempts_per90"
    assert explanation.measurement == 10
    assert explanation.weight == 1
    assert explanation.points == 100


def test_default_templates_have_expected_contributions():
    result = rank(
        [
            sample(1, counts=MetricCounts(100, 50)),
            sample(2, counts=MetricCounts(50, 50)),
        ]
    )

    assert (
        result.candidates[0].score == 55
    )  # 40 volume + 0 completion + 15 neutral distribution
    assert result.candidates[1].score == pytest.approx(45)
    assert result.candidates[0].score == pytest.approx(
        sum(c.points for c in result.candidates[0].contributions)
    )


def test_defensive_template_uses_only_verified_existing_rates():
    result = rank(
        [
            sample(1, counts=MetricCounts(100, 80, 10, 10, 5)),
            sample(2, counts=MetricCounts(50, 40, 30, 20, 15)),
        ],
        BWM,
    )

    assert result.candidates[0].eligibility.player.player_id == 2
    assert result.candidates[0].score == 85
    assert set(result.candidates[0].measurements) == {
        "pass_attempts_per90",
        "accurate_passes_per90",
        "pass_completion_pct",
        "interceptions_per90",
        "successful_defensive_duels_per90",
    }


def test_midrank_ties_and_reference_ids_are_deterministic():
    players = [sample(3, counts=MetricCounts(200, 100)), sample(2), sample(1)]
    first = rank(players, weights={"pass_attempts_per90": 1})
    second = rank(list(reversed(players)), weights={"pass_attempts_per90": 100})

    assert first == second
    assert [r.score for r in first.candidates] == [100, 25, 25]
    assert [r.eligibility.player.player_id for r in first.candidates] == [3, 1, 2]
    assert first.reference_ids == ((1, 10), (2, 10), (3, 10))


def test_missing_required_metrics_are_excluded_from_score_and_reference():
    incomplete = sample(
        1, counts=MetricCounts(10000, 9000, passes_with_unknown_outcome=1)
    )
    result = rank([incomplete, sample(2)])

    assert result.reference_ids == ((2, 10),)
    assert result.candidates[0].score == pytest.approx(50)
    missing = result.candidates[1]
    assert missing.score is None
    assert missing.measurements["pass_completion_pct"] is None
    assert missing.measurements["accurate_passes_per90"] is None
    assert any("unavailable required metric" in r for r in missing.reasons)


def test_explicitly_disabled_metric_can_be_unavailable():
    incomplete = sample(1, counts=MetricCounts(100, 80, passes_with_unknown_outcome=1))
    result = rank(
        [incomplete], weights={"pass_attempts_per90": 1, "pass_completion_pct": 0}
    )

    assert result.candidates[0].score == 50
    assert result.candidates[0].measurements["pass_completion_pct"] is None
    assert len(result.candidates[0].contributions) == 1
    assert result.weights["pass_completion_pct"] == 0


def test_unknown_defending_outcomes_withhold_ball_winning_score():
    player = sample(1, counts=MetricCounts(100, 80, 20, 10, 5, 0, 1))

    assert rank([player], BWM).candidates[0].score is None
    assert rank([player], DLP).candidates[0].score == pytest.approx(50)


def test_missing_rated_counts_never_turn_into_zero_measurements():
    result = rank([replace(sample(1), rated=None)], BWM)

    assert result.candidates[0].score is None
    assert all(v is None for v in result.candidates[0].measurements.values())
    assert "rated event counts unavailable" in result.candidates[0].reasons


def test_unused_bench_is_not_added_to_appearance_coverage():
    player = sample(1, rated=6)
    unmatched = PlayerMatchMetrics(99, 10, 1, False, None, 1, MetricCounts(), ())
    player = replace(player, matches=player.matches + (unmatched,))
    candidate = rank([player]).candidates[0].eligibility

    assert candidate.appearance_coverage == 0.6
    assert candidate.recorded_appearances == 10
    assert candidate.unrecorded_event_matches == 1


@pytest.mark.parametrize(
    "weights",
    [
        {},
        {"pass_attempts_per90": 0},
        {"pass_attempts_per90": -1},
        {"pass_attempts_per90": float("nan")},
        {"pass_attempts_per90": float("inf")},
        {"pass_attempts_per90": True},
        {"pass_attempts_per90": "1"},
        {"progressive_passes_per90": 1},
        {"interceptions_per90": 1},
    ],
)
def test_invalid_weights_are_rejected(weights):
    with pytest.raises(ValueError):
        normalize_weights(DLP, weights)


def test_large_finite_weights_normalize_without_overflow():
    weights = normalize_weights(
        DLP, {"pass_attempts_per90": 1e308, "pass_completion_pct": 1e308}
    )

    assert weights == {"pass_attempts_per90": 0.5, "pass_completion_pct": 0.5}


@pytest.mark.parametrize(
    "minutes,coverage",
    [
        (-1, 0.5),
        (True, 0.5),
        (float("inf"), 0.5),
        (600, -0.1),
        (600, 1.1),
        (600, float("nan")),
        (600, False),
    ],
)
def test_invalid_thresholds_are_rejected(minutes, coverage):
    with pytest.raises(ValueError):
        EligibilityThresholds(minutes, coverage)


def test_invalid_reviews_duplicate_metrics_and_unknown_roles_are_rejected():
    with pytest.raises(ValueError, match="requires evidence"):
        PositionReview("included")
    with pytest.raises(ValueError, match="status"):
        PositionReview("midfielder")
    with pytest.raises(ValueError, match="absent"):
        assess_eligibility([sample(1)], {(1, 20): REVIEW})
    with pytest.raises(ValueError, match="duplicate"):
        assess_eligibility([sample(1), sample(1)], {})
    with pytest.raises(ValueError, match="unknown tactical role"):
        rank([sample(1)], "style_similarity")


def test_empty_cohort_has_no_scores():
    result = rank([])

    assert result.reference_ids == ()
    assert result.candidates == ()


def test_ineligible_outlier_cannot_change_reference_percentiles():
    result = rank(
        [
            sample(1),
            sample(2, counts=MetricCounts(200, 160)),
            sample(3, minutes=599, counts=MetricCounts(100000, 99999)),
        ],
        weights={"pass_attempts_per90": 1},
    )

    assert result.reference_ids == ((1, 10), (2, 10))
    assert [r.score for r in result.candidates] == [100, 0, None]


def test_reviewed_transfer_rows_are_scored_separately_with_team_tie_order():
    result = rank([sample(1, team=20), sample(1, team=10)])

    assert result.reference_ids == ((1, 10), (1, 20))
    assert [r.eligibility.player.team_id for r in result.candidates] == [10, 20]
    assert all(r.eligibility.player.rated_minutes == 900 for r in result.candidates)


def test_zero_defensive_counts_are_valid_measurements_not_missing():
    result = rank([sample(1, counts=MetricCounts(100, 80))], BWM)

    assert result.candidates[0].measurements["interceptions_per90"] == 0
    assert result.candidates[0].measurements["successful_defensive_duels_per90"] == 0
    assert result.candidates[0].score == pytest.approx(50)


def test_no_pass_completion_sample_is_not_scored_as_zero_completion():
    result = rank([sample(1, counts=MetricCounts())])

    assert result.candidates[0].score is None
    assert result.candidates[0].measurements["pass_completion_pct"] is None
