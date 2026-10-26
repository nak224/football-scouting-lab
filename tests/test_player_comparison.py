"""Direct/statistical comparisons: all samples and identities are synthetic."""

from copy import deepcopy
from dataclasses import replace

import pytest

from football_scouting_lab import explorer

from .test_explorer import dataset, sample


def test_fixed_shared_population_and_score_formula_with_raw_differences():
    data = dataset()
    pair = explorer.compare_pair(data, (1, 10), (2, 10))
    assert pair.reference == explorer.compare_player(data, (1, 10))
    assert pair.reference.peer_ids == pair.candidate.peer_ids == ((1, 10), (2, 10))
    assert pair.similarity == 62.5  # differences 50, 0, 50, 50
    assert pair.common_metrics == explorer.FEATURES
    rows = explorer.pair_rows(pair)
    assert rows[0]["A"] == 10 and rows[0]["B"] == 20
    assert rows[0]["B − A"] == 10
    assert rows[0]["A percentile"] == 25 and rows[0]["B percentile"] == 75
    assert all(row["Peers"] == 2 for row in rows)
    all_players = explorer.compare_pair(data, (1, 10), (3, 10), mode="All players")
    assert len(all_players.reference.peer_ids) == 4
    assert all_players.reference.peer_ids == all_players.candidate.peer_ids
    assert all_players.reference.features[0].percentile == 37.5


def test_rankings_ignore_reviews_are_deterministic_and_never_mutate_samples():
    data = dataset()
    original = deepcopy(data)
    result = explorer.similar_profiles(data, (1, 10), mode="All players")
    assert len(result.matches) == 3
    assert all(0 <= pair.similarity <= 100 for pair in result.matches)
    assert result.matches == tuple(
        sorted(
            result.matches,
            key=lambda pair: (-pair.similarity, *pair.candidate.player_team_id),
        )
    )
    assert result == explorer.similar_profiles(
        replace(data, custom_reviews={}), (1, 10), mode="All players"
    )
    reverse = replace(
        data,
        metrics=replace(data.metrics, players=tuple(reversed(data.metrics.players))),
    )
    assert result == explorer.similar_profiles(reverse, (1, 10), mode="All players")
    assert data == original


def test_five_matches_ties_constant_features_and_transfers_keep_original_ids():
    players = (
        sample(1),
        sample(1, team=20),
        sample(2, team=20),
        *(sample(p) for p in (2, 3, 4, 5, 6, 7)),
    )
    data = dataset(players)
    data = replace(data, player_positions={p.player_id: "Midfielder" for p in players})
    result = explorer.similar_profiles(data, (1, 10))
    assert [pair.candidate.player_team_id for pair in result.matches] == [
        (2, 10),
        (2, 20),
        (3, 10),
        (4, 10),
        (5, 10),
    ]
    assert all(pair.similarity == 100 for pair in result.matches)
    assert not any(key[0] == 1 for key, _ in result.exclusions)
    for pair in result.matches:
        assert all(feature.percentile == 50 for feature in pair.reference.features)
        assert pair.reference.peer_ids == pair.candidate.peer_ids
    with pytest.raises(ValueError, match="underlying player"):
        explorer.compare_pair(data, (1, 10), (1, 20))


def test_missing_candidate_feature_does_not_gain_advantage_from_partial_distance():
    first, second, third, fourth = dataset().metrics.players
    second = replace(second, rated=replace(second.rated, passes_with_unknown_outcome=1))
    data = dataset((first, second, third, fourth))
    result = explorer.similar_profiles(data, (1, 10), mode="All players")
    assert len(result.feature_basis) == 4
    reasons = dict(result.exclusions)[(2, 10)]
    assert any("Pass completion" in reason for reason in reasons)
    assert (2, 10) not in {pair.candidate.player_team_id for pair in result.matches}
    pair = explorer.compare_pair(data, (1, 10), (2, 10), mode="All players")
    assert len(pair.common_metrics) == 3  # still usable as a manual radar
    assert pair.similarity is None
    rows = explorer.pair_rows(pair)
    assert rows[1]["B"] is None and rows[1]["B − A"] is None


def test_partial_reference_uses_the_same_three_features_for_every_match():
    players = list(dataset().metrics.players)
    players[0] = replace(
        players[0], rated=replace(players[0].rated, passes_with_unknown_outcome=1)
    )
    data = dataset(tuple(players))
    result = explorer.similar_profiles(data, (1, 10), mode="All players")
    assert len(result.feature_basis) == 3
    assert "pass_completion_pct" not in result.feature_basis
    assert len(result.matches) == 3
    assert all(pair.common_metrics == result.feature_basis for pair in result.matches)


@pytest.mark.parametrize("missing", [None, 0, 599])
def test_inadequate_samples_stay_available_as_raw_manual_comparisons(missing):
    first, second, third, fourth = dataset().metrics.players
    second = replace(second, rated_minutes=missing)
    data = dataset((first, second, third, fourth))
    pair = explorer.compare_pair(data, (1, 10), (2, 10))
    assert pair.similarity is None
    assert any("600" in reason for reason in pair.reasons)
    assert (2, 10) in dict(explorer.similar_profiles(data, (1, 10)).exclusions)


def test_ineligible_reference_and_tiny_groups_never_invent_a_score():
    data = dataset((sample(1), sample(2, minutes=400)))
    result = explorer.similar_profiles(data, (1, 10))
    assert not result.matches and result.warnings
    assert result.feature_basis == ()
    low = explorer.similar_profiles(data, (2, 10))
    assert any("600" in reason for reason in low.warnings)
    assert not low.matches
    single = explorer.similar_profiles(dataset((sample(1),)), (1, 10))
    assert not single.matches and not single.exclusions


def test_unknown_and_cross_positions_require_explicit_all_player_scope():
    data = dataset()
    same = explorer.similar_profiles(data, (1, 10))
    assert len(same.matches) == 1
    assert "position" in " ".join(dict(same.exclusions)[(3, 10)])
    with pytest.raises(ValueError, match="All players"):
        explorer.compare_pair(data, (1, 10), (3, 10))
    unknown = explorer.similar_profiles(data, (4, 10))
    assert not unknown.matches and unknown.warnings
    all_players = explorer.similar_profiles(data, (4, 10), mode="All players")
    assert len(all_players.matches) == 3


def test_changing_b_cannot_refit_a_or_any_feature_population():
    data = dataset()
    pairs = [
        explorer.compare_pair(data, (1, 10), key, mode="All players")
        for key in ((2, 10), (3, 10), (4, 10))
    ]
    assert all(pair.reference == pairs[0].reference for pair in pairs)
    assert all(
        [row.peer_count for row in pair.candidate.features]
        == [row.peer_count for row in pairs[0].reference.features]
        for pair in pairs
    )
    with pytest.raises(ValueError, match="absent"):
        explorer.compare_pair(data, (1, 10), (999, 10))
