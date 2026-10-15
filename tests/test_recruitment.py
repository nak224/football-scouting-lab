"""Synthetic season metrics and position reviews; no third-party fixtures."""

from copy import deepcopy
from dataclasses import replace

import pytest

from football_scouting_lab import recruitment
from football_scouting_lab.metrics import (
    MetricCounts,
    PlayerMatchMetrics,
    PlayerSeasonMetrics,
)
from football_scouting_lab.roles import (
    EligibilityThresholds,
    PositionReview,
    score_role,
)
from football_scouting_lab.similarity import compare_styles

BWM = "ball_winning_midfielder"
DLP = "deep_lying_playmaker"
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
            ("synthetic timing warning",),
        )
        for number in range(1, 11)
    )
    return PlayerSeasonMetrics(player_id, team, matches, counts, counts, minutes)


def rank(players, role=BWM, *, reviews=None, **kwargs):
    reviews = (
        {(p.player_id, p.team_id): REVIEW for p in players}
        if reviews is None
        else reviews
    )
    return recruitment.rank_replacements(players, reviews, (1, 10), role, **kwargs)


def row(result, key):
    return next(c for c in result.candidates if c.candidate_id == key)


def contrasting_players():
    return [sample(1), sample(2), sample(3, counts=MetricCounts(200, 180, 40, 20, 15))]


@pytest.mark.parametrize("priority,first", [(1, (2, 10)), (0, (3, 10))])
def test_endpoint_priorities_match_the_selected_component_for_complete_candidates(
    priority, first
):
    result = rank(contrasting_players(), style_priority=priority)

    assert result.shortlist[0].candidate_id == first
    assert len(result.shortlist) == 2
    for candidate in result.shortlist:
        assert candidate.combined_score == pytest.approx(
            candidate.style.score if priority == 1 else candidate.role.score
        )
        assert candidate.style_contribution == pytest.approx(
            priority * candidate.style.score
        )
        assert candidate.role_contribution == pytest.approx(
            (1 - priority) * candidate.role.score
        )


def test_default_equal_priorities_and_weighted_points_remain_explainable():
    result = rank(contrasting_players())
    candidate = row(result, (2, 10))

    assert result.style_priority == 0.5
    assert candidate.style.score == 100
    assert candidate.role.score == pytest.approx(25)
    assert candidate.style_contribution == 50
    assert candidate.role_contribution == pytest.approx(12.5)
    assert candidate.combined_score == pytest.approx(62.5)
    assert (
        candidate.combined_score
        == candidate.style_contribution + candidate.role_contribution
    )
    assert candidate.style.differences
    assert candidate.role.contributions
    assert candidate.style.candidate.player.rated_minutes == 900
    assert candidate.style.candidate.appearance_coverage == 1
    assert candidate.role.eligibility.player.matches[0].warnings == (
        "synthetic timing warning",
    )


def test_priority_changes_order_without_changing_component_results():
    style_favored = rank(contrasting_players(), style_priority=0.75)
    role_favored = rank(contrasting_players(), style_priority=0.25)

    assert style_favored.shortlist[0].candidate_id == (2, 10)
    assert role_favored.shortlist[0].candidate_id == (3, 10)
    assert style_favored.style == role_favored.style
    assert style_favored.role == role_favored.role


@pytest.mark.parametrize("priority", [0, 0.5, 1])
def test_missing_style_score_excludes_even_with_zero_style_weight(priority):
    incomplete = sample(2, counts=MetricCounts(100, 80, 20, 10, 5, 1))
    result = rank([sample(1), incomplete], style_priority=priority)
    candidate = row(result, (2, 10))

    assert candidate.style.score is None
    assert candidate.role.score is not None
    assert candidate.style_contribution is None
    assert candidate.role_contribution is not None
    assert candidate.combined_score is None
    assert "style score unavailable" in candidate.reasons
    assert any("pass_completion_pct" in reason for reason in candidate.reasons)
    assert result.shortlist == ()


@pytest.mark.parametrize("priority", [0, 0.5, 1])
def test_missing_role_score_excludes_even_with_zero_role_weight(priority):
    incomplete = sample(2, counts=MetricCounts(100, 80, 20, 10, 5, 1))
    result = rank(
        [sample(1), incomplete],
        DLP,
        style_priority=priority,
        style_weights={"pass_attempts_per90": 1},
    )
    candidate = row(result, (2, 10))

    assert candidate.style.score is not None
    assert candidate.role.score is None
    assert candidate.style_contribution is not None
    assert candidate.role_contribution is None
    assert candidate.combined_score is None
    assert "role score unavailable" in candidate.reasons
    assert result.shortlist == ()


def test_source_cohorts_and_weights_are_preserved_instead_of_refitting_intersection():
    players = [
        sample(1),
        sample(2),
        sample(3, counts=MetricCounts(10000, 8000, passes_with_unknown_outcome=1)),
    ]
    reviews = {(p.player_id, p.team_id): REVIEW for p in players}
    weights = {"pass_attempts_per90": 2}
    result = recruitment.rank_replacements(
        players,
        reviews,
        (1, 10),
        DLP,
        style_weights=weights,
        role_weights={"accurate_passes_per90": 1},
    )

    assert result.style.normalization_ids == ((1, 10), (2, 10), (3, 10))
    assert result.role.reference_ids == ((1, 10), (2, 10))
    assert result.style.weights == {"pass_attempts_per90": 1}
    assert result.role.weights == {"accurate_passes_per90": 1}
    assert result.style == compare_styles(players, reviews, (1, 10), weights=weights)
    assert result.role == score_role(
        players, reviews, DLP, weights={"accurate_passes_per90": 1}
    )
    assert weights == {"pass_attempts_per90": 2}


def test_reference_needs_style_eligibility_but_not_the_selected_role_measurements():
    reference = sample(1, counts=MetricCounts(100, 80, 20, 10, 5, 1))
    result = rank([reference, sample(2)], DLP, style_weights={"pass_attempts_per90": 1})

    assert result.reference_id == (1, 10)
    assert result.style.normalization_ids == ((1, 10), (2, 10))
    assert result.role.reference_ids == ((2, 10),)
    assert row(result, (1, 10)).role.score is None
    assert result.shortlist[0].role.score == pytest.approx(50)


def test_reference_is_never_recommended_under_any_historical_team():
    result = rank([sample(1), sample(1, team=20), sample(2)], limit=1)

    assert [c.candidate_id for c in result.shortlist] == [(2, 10)]
    for key in [(1, 10), (1, 20)]:
        assert row(result, key).style.score is not None
        assert row(result, key).role.score is not None
        assert row(result, key).combined_score is None
        assert "same underlying player as reference" in row(result, key).reasons


def test_transfer_rows_remain_separate_and_ties_use_player_then_team_ids():
    players = [sample(3), sample(2, team=20), sample(1), sample(2, team=10)]
    first = rank(players)
    second = rank(list(reversed(players)))

    assert first == second
    assert [c.candidate_id for c in first.shortlist] == [(2, 10), (2, 20), (3, 10)]
    assert all(c.style.candidate.player.rated_minutes == 900 for c in first.shortlist)


def test_empty_and_underfilled_shortlists_are_reported_without_padding():
    empty = rank([sample(1), sample(1, team=20)], limit=3)
    underfilled = rank([sample(1), sample(2)], limit=3)

    assert empty.shortlist == ()
    assert any("no complete replacement" in w for w in empty.warnings)
    assert any("only 0" in w for w in empty.warnings)
    assert len(underfilled.shortlist) == 1
    assert any("requested 3 rows; only 1" in w for w in underfilled.warnings)


def test_zero_limit_retains_full_candidate_diagnostics():
    result = rank([sample(1), sample(2)], limit=0)

    assert result.shortlist == ()
    assert len(result.candidates) == 2
    assert row(result, (2, 10)).combined_score is not None
    assert not result.warnings


def test_eligibility_thresholds_and_review_reasons_are_preserved():
    players = [sample(1), sample(2, minutes=450, rated_matches=5), sample(3)]
    reviews = {(1, 10): REVIEW, (2, 10): REVIEW}
    default = rank(players, reviews=reviews)
    thresholds = EligibilityThresholds(400, 0.5)
    relaxed = rank(players, reviews=reviews, thresholds=thresholds)

    assert row(default, (2, 10)).combined_score is None
    assert any(
        "below minimum rated minutes" in r for r in row(default, (2, 10)).reasons
    )
    assert any("unverified" in r for r in row(relaxed, (3, 10)).reasons)
    assert [c.candidate_id for c in relaxed.shortlist] == [(2, 10)]
    assert relaxed.style.thresholds == relaxed.role.thresholds == thresholds


def test_calls_source_algorithms_once_with_same_generator_data_and_does_not_mutate_results(
    monkeypatch,
):
    captured = {}
    snapshots = {}
    for name, function in [
        ("compare_styles", compare_styles),
        ("score_role", score_role),
    ]:

        def capture(*args, _name=name, _function=function, **kwargs):
            assert _name not in captured
            result = _function(*args, **kwargs)
            captured[_name] = result
            snapshots[_name] = deepcopy(result)
            return result

        monkeypatch.setattr(recruitment, name, capture)
    players = contrasting_players()
    reviews = {(p.player_id, p.team_id): REVIEW for p in players}
    original_players = deepcopy(players)

    result = recruitment.rank_replacements(iter(players), reviews, (1, 10), BWM)

    assert result.style is captured["compare_styles"]
    assert result.role is captured["score_role"]
    assert captured == snapshots
    assert players == original_players
    for candidate in result.candidates:
        assert candidate.style is next(
            s
            for s in result.style.candidates
            if s.candidate_id == candidate.candidate_id
        )
        assert candidate.role is next(
            r
            for r in result.role.candidates
            if (r.eligibility.player.player_id, r.eligibility.player.team_id)
            == candidate.candidate_id
        )


@pytest.mark.parametrize(
    "priority", [-0.1, 1.1, float("nan"), float("inf"), True, "0.5", None, 10**1000]
)
def test_invalid_priorities_fail(priority):
    with pytest.raises(ValueError, match="style_priority"):
        rank([sample(1), sample(2)], style_priority=priority)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"style_weights": {}},
        {"role_weights": {}},
        {"style_weights": {"pass_attempts_per90": -1}},
        {"style_weights": {"interceptions_per90": float("inf")}},
        {"style_weights": {"role_fit": 1}},
        {"role_weights": {"interceptions_per90": 0}},
        {"role_weights": {"interceptions_per90": True}},
        {"role_weights": {"interceptions_per90": float("nan")}},
        {"role_weights": {"progressive_passes_per90": 1}},
    ],
)
def test_component_weight_validation_is_not_bypassed_at_endpoints(kwargs):
    for priority in (0, 1):
        with pytest.raises(ValueError):
            rank([sample(1), sample(2)], style_priority=priority, **kwargs)


@pytest.mark.parametrize("limit", [-1, True, 1.5, "3"])
def test_invalid_shortlist_limits_fail(limit):
    with pytest.raises(ValueError, match="shortlist limit"):
        rank([sample(1), sample(2)], limit=limit)


def test_invalid_reference_or_role_and_empty_input_fail_explicitly():
    with pytest.raises(ValueError, match="reference"):
        rank([])
    with pytest.raises(ValueError, match="position review: unverified"):
        rank([sample(1), sample(2)], reviews={}, style_priority=0)
    with pytest.raises(ValueError, match="unknown tactical role"):
        rank([sample(1), sample(2)], role="unknown")


def test_missing_both_components_never_turns_into_zero():
    result = rank([sample(1), replace(sample(2), rated=None)])
    candidate = row(result, (2, 10))

    assert candidate.style.score is candidate.role.score is None
    assert candidate.style_contribution is candidate.role_contribution is None
    assert candidate.combined_score is None
    assert result.shortlist == ()
