"""Discovery comparisons use explicitly synthetic aggregate measurements only."""

import json
from copy import deepcopy
from dataclasses import replace

import pytest

from football_scouting_lab import explorer
from football_scouting_lab.metrics import (
    MetricCounts,
    PlayerMatchMetrics,
    PlayerSeasonMetrics,
    SeasonMetrics,
)
from football_scouting_lab.ui_data import (
    ScoutingData,
    load_fictional_demo,
    load_scouting_data,
)


def sample(
    player, *, team=10, passes=100, accurate=80, interceptions=10, wins=5, minutes=900
):
    counts = MetricCounts(passes, accurate, interceptions, wins, wins)
    match = PlayerMatchMetrics(1, team, player, True, minutes, passes, counts, ())
    return PlayerSeasonMetrics(player, team, (match,), counts, counts, minutes)


def dataset(players=None):
    players = players or (
        sample(1),
        sample(2, passes=200, accurate=160, interceptions=20, wins=0),
        sample(3, passes=50, accurate=30),
        sample(4, passes=300, accurate=240),
    )
    return ScoutingData(
        SeasonMetrics(
            (),
            tuple(players),
            0,
            frozenset(),
            frozenset(),
            frozenset(),
            frozenset(),
            frozenset(),
        ),
        {1: "Älex", 2: "Blair", 3: "Casey", 4: "Drew"},
        {10: "Fictional Club", 20: "Another Club"},
        player_positions={
            1: "Midfielder",
            2: "Midfielder",
            3: "Defender",
            4: "Unknown",
        },
    )


def test_combined_filters_are_independent_of_recruitment_reviews():
    data = dataset()
    original = deepcopy(data)
    rows = explorer.discovery_rows(
        data,
        query=" ÄL ",
        league=explorer.LEAGUE,
        team_id=10,
        player_position="Midfielder",
    )
    assert [(row["Name"], row["Player ID"], row["Team ID"]) for row in rows] == [
        ("Älex", 1, 10)
    ]
    assert rows == explorer.discovery_rows(
        replace(data, custom_reviews={}),
        query="äl",
        team_id=10,
        player_position="Midfielder",
    )
    assert explorer.discovery_rows(data, query="Älex", player_position="Defender") == []
    assert explorer.discovery_rows(data, league="Unprovided league") == []
    assert explorer.discovery_rows(data, team_id=999) == []
    assert explorer.discovery_rows(data, player_position="CM") == []
    assert "Position review" not in rows[0]
    assert explorer.discovery_rows(data, player_position="Unknown")[0]["Player ID"] == 4
    assert data == original
    assert explorer.compare_player(data, (1, 10)) == explorer.compare_player(
        replace(data, custom_reviews={}), (1, 10)
    )


def test_transfers_retain_original_team_rows_and_selection_identity():
    data = dataset((sample(1), sample(1, team=20, passes=200, minutes=600), sample(2)))
    rows = explorer.discovery_rows(data, query="Älex")
    assert [row["Team ID"] for row in rows] == [10, 20]
    assert rows[0]["Pass attempts /90"] == 10
    assert rows[1]["Pass attempts /90"] == 30
    assert explorer.selected_player(rows, [1]) == (1, 20)
    assert explorer.compare_player(data, (1, 20)).peer_ids == (
        (1, 10),
        (1, 20),
        (2, 10),
    )


@pytest.mark.parametrize("indices", [[], [0, 1], [-1], [2], [True], [0.0]])
def test_invalid_selection_is_not_assigned_to_another_player(indices):
    assert (
        explorer.selected_player(
            explorer.discovery_rows(dataset(), query="Älex"), indices
        )
        is None
    )


def test_same_position_and_all_players_midrank_percentiles():
    data = dataset()
    same = explorer.compare_player(data, (1, 10))
    all_players = explorer.compare_player(data, (1, 10), mode="All players")
    assert same.peer_ids == ((1, 10), (2, 10))
    assert [row.percentile for row in same.features] == [25, 50, 25, 75]
    assert len(all_players.peer_ids) == 4
    assert all_players.features[0].percentile == 37.5
    assert same.features[0].value == 10  # existing rated passes /90
    assert all(row.peer_count == 2 for row in same.features)
    # Input ordering cannot change peers, features, ties or chart input.
    reversed_data = replace(
        data,
        metrics=replace(data.metrics, players=tuple(reversed(data.metrics.players))),
    )
    assert explorer.compare_player(reversed_data, (1, 10)) == same


def test_default_600_minutes_population_can_compare_a_low_minute_target():
    data = dataset(
        (sample(1, minutes=599), sample(2, minutes=600), sample(3, minutes=900))
    )
    result = explorer.compare_player(data, (1, 10), mode="All players")
    assert result.peer_ids == ((2, 10), (3, 10))
    assert result.features[0].value == pytest.approx(9000 / 599)
    assert result.features[0].percentile is not None
    assert explorer.compare_player(data, (1, 10), min_minutes=10000).peer_ids == ()


def test_unknown_positions_are_not_inferred_or_treated_as_a_position_group():
    data = dataset()
    assert explorer.position(data, 999) == "Unknown"
    assert (
        explorer.position(replace(data, player_positions={1: "Central Midfielder"}), 1)
        == "Unknown"
    )
    result = explorer.compare_player(data, (4, 10))
    assert result.peer_ids == ()
    assert all(row.percentile is None for row in result.features)
    assert len(explorer.compare_player(data, (4, 10), mode="All players").peer_ids) == 4


def test_missing_values_are_excluded_per_feature_and_radar_never_pads_zeroes():
    data = dataset()
    second = data.metrics.players[1]
    partial = replace(
        second, rated=replace(second.rated, passes_with_unknown_outcome=1)
    )
    data = replace(
        data, metrics=replace(data.metrics, players=(data.metrics.players[0], partial))
    )
    result = explorer.compare_player(data, (1, 10))
    assert [row.peer_count for row in result.features] == [2, 1, 2, 2]
    assert result.features[1].percentile is None
    assert len(explorer.radar_features(result)) == 3
    missing_duels = replace(
        partial, rated=replace(partial.rated, defensive_duels_with_unknown_outcome=1)
    )
    data = replace(
        data,
        metrics=replace(data.metrics, players=(data.metrics.players[0], missing_duels)),
    )
    assert explorer.radar_features(explorer.compare_player(data, (1, 10))) == ()
    partial_result = explorer.compare_player(data, (2, 10))
    assert partial_result.features[1].value is None
    assert partial_result.features[3].value is None


@pytest.mark.parametrize("minutes", [None, 0, -1, float("nan"), float("inf"), True])
def test_invalid_time_never_becomes_zero_measurements(minutes):
    player = replace(sample(1), rated_minutes=minutes)
    assert all(value is None for value in explorer.measurements(player).values())


def test_missing_rated_counts_and_zero_passes_stay_distinct():
    assert all(
        value is None
        for value in explorer.measurements(replace(sample(1), rated=None)).values()
    )
    values = explorer.measurements(
        sample(1, passes=0, accurate=0, interceptions=0, wins=0)
    )
    assert values == dict(zip(explorer.FEATURES, [0, None, 0, 0], strict=True))


def test_tiny_and_constant_groups_have_explicit_deterministic_outcomes():
    single = explorer.compare_player(dataset((sample(1),)), (1, 10))
    assert all(
        row.percentile is None and row.peer_count == 1 for row in single.features
    )
    assert explorer.radar_features(single) == ()
    constant = explorer.compare_player(dataset((sample(1), sample(2))), (1, 10))
    assert all(row.percentile == 50 for row in constant.features)
    assert explorer.radar_features(constant) == constant.features


@pytest.mark.parametrize("minutes", [0, -1, float("inf"), float("nan"), True])
def test_invalid_comparison_thresholds_fail_clearly(minutes):
    with pytest.raises(ValueError, match="finite and positive"):
        explorer.compare_player(dataset(), (1, 10), min_minutes=minutes)


def test_invalid_profile_and_comparison_mode_are_explicit():
    with pytest.raises(ValueError, match="absent"):
        explorer.compare_player(dataset(), (1, 999))
    with pytest.raises(ValueError, match="comparison mode"):
        explorer.compare_player(dataset(), (1, 10), mode="CM")
    with pytest.raises(ValueError, match="duplicate"):
        explorer.compare_player(dataset((sample(1), sample(1))), (1, 10))


def test_loader_retains_only_original_broad_positions_and_sources_stay_separate(
    ui_data_dir,
):
    path = ui_data_dir / "players.json"
    players = json.loads(path.read_text())
    for player, role in zip(
        players,
        [
            "Goalkeeper",
            "Defender",
            "Midfielder",
            "Forward",
            "CM",
            None,
            "Midfielder",
            "Forward",
        ],
        strict=True,
    ):
        player["role"] = {"name": role}
    path.write_text(json.dumps(players))
    real_format = load_scouting_data(str(ui_data_dir))
    assert [
        real_format.player_positions[player]
        for player in (101, 102, 103, 104, 105, 106)
    ] == ["Goalkeeper", "Defender", "Midfielder", "Forward", "Unknown", "Unknown"]
    assert (
        explorer.discovery_rows(real_format, query="Synthetic Player A")[0]["Position"]
        == "Goalkeeper"
    )
    fictional = load_fictional_demo()
    assert set(fictional.player_positions.values()) == {"Midfielder"}
    assert set(fictional.player_positions).isdisjoint(real_format.player_positions)
    assert real_format.player_positions[101] == "Goalkeeper"
