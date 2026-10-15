"""All matches and actions below are explicitly fictional, not source samples."""

import json

import pytest

from football_scouting_lab.metrics import MetricCounts, calculate_metrics
from football_scouting_lab.wyscout import load_events, load_season


def action(event_id, subtype, tags=(), *, match=1001, team=201, player=101):
    return {
        "id": 1,
        "matchId": match,
        "teamId": team,
        "playerId": player,
        "eventId": event_id,
        "eventName": "Synthetic action",
        "subEventId": subtype,
        "subEventName": "Synthetic subtype",
        "tags": [{"id": tag} for tag in tags],
        "positions": [],
        "matchPeriod": "1H",
        "eventSec": 30,
    }


@pytest.fixture
def metric_data(synthetic_data_dir):
    path = synthetic_data_dir / "matches_Germany.json"
    matches = json.loads(path.read_text())
    for match in matches:
        match["duration"] = "Regular"
        for team in match["teamsData"].values():
            for p in team["formation"]["lineup"] + team["formation"]["bench"]:
                p["redCards"] = "0"
    path.write_text(json.dumps(matches))
    events = []
    for mid, tid, first, second in [(1001, 201, 47, 49), (1002, 202, 45, 45)]:
        for period, minute in [("1H", first), ("2H", second)]:
            event = action(5, 51, match=mid, team=tid, player=0)
            event.update(matchPeriod=period, eventSec=minute * 60)
            events.append(event)
    save_events(synthetic_data_dir, events)
    return synthetic_data_dir


def save_events(data_dir, events):
    for number, event in enumerate(events, 1):
        event["id"] = number
    (data_dir / "events_Germany.json").write_text(json.dumps(events))


def run(data_dir, actions=()):
    path = data_dir / "events_Germany.json"
    save_events(data_dir, json.loads(path.read_text()) + list(actions))
    metadata = load_season(data_dir)
    return calculate_metrics(metadata, load_events(data_dir, metadata))


def player(result, player_id=101, team_id=201):
    return next(
        p for p in result.players if (p.player_id, p.team_id) == (player_id, team_id)
    )


@pytest.mark.parametrize("subtype", [80, 81, 82, 83, 84, 85, 86, ""])
def test_pass_type_and_accuracy_preserve_interception_tag(metric_data, subtype):
    row = player(run(metric_data, [action(8, subtype, [1801, 1401, 1401])]))

    assert row.observed == MetricCounts(
        pass_attempts=1, accurate_passes=1, interceptions=1
    )
    assert row.observed.pass_completion_pct == 100
    assert row.per90["pass_attempts"] == pytest.approx(90 / 96)
    assert row.matches[0].match_id == 1001
    assert row.matches[0].minutes == 96


@pytest.mark.parametrize("subtype", [30, 31, 32, 34, 36])
def test_set_pieces_are_outside_the_pass_family(metric_data, subtype):
    row = player(run(metric_data, [action(3, subtype, [1801])]))

    assert row.observed.pass_attempts == 0
    assert row.observed.pass_completion_pct is None


@pytest.mark.parametrize(
    ("event_type", "subtype", "tags", "attempts", "won"),
    [
        (1, 12, [703], 1, 1),
        (1, 12, [703, 1802], 1, 1),
        (1, 12, [701, 1801], 1, 0),
        (1, 12, [702], 1, 0),
        (1, 10, [703], 0, 0),
        (1, 11, [703], 0, 0),
        (1, 13, [703], 0, 0),
        (7, 12, [703], 0, 0),
    ],
)
def test_defensive_duel_success_requires_defending_subtype_and_won_tag(
    metric_data, event_type, subtype, tags, attempts, won
):
    row = player(run(metric_data, [action(event_type, subtype, tags)]))

    assert row.observed.defensive_duel_attempts == attempts
    assert row.observed.successful_defensive_duels == won


@pytest.mark.parametrize("tags", [[], [1801, 1802]])
def test_missing_or_conflicting_pass_outcome_is_explicit(metric_data, tags):
    result = run(metric_data, [action(8, 85, tags), action(8, 85, [1801])])
    row = player(result)

    assert row.observed.pass_attempts == 2
    assert row.observed.accurate_passes == 1
    assert row.observed.passes_with_unknown_outcome == 1
    assert row.observed.pass_completion_pct is None
    assert row.per90["accurate_passes"] is None
    assert row.per90["pass_attempts"] == pytest.approx(180 / 96)
    assert len(result.ambiguous_pass_event_ids) == 1


@pytest.mark.parametrize("tags", [[], [701, 703]])
def test_unresolved_defensive_outcomes_do_not_become_losses(metric_data, tags):
    result = run(metric_data, [action(1, 12, tags)])
    row = player(result)

    assert row.rated.defensive_duels_with_unknown_outcome == 1
    assert row.per90["successful_defensive_duels"] is None
    assert len(result.ambiguous_defensive_duel_event_ids) == 1


def test_transfers_have_separate_historical_team_rows(metric_data):
    result = run(
        metric_data,
        [
            action(8, 85, [1801]),
            action(8, 85, [1802], match=1002, team=202),
        ],
    )

    assert player(result).rated_minutes == 96
    assert player(result, team_id=202).rated_minutes == 90
    assert player(result).observed.pass_completion_pct == 100
    assert player(result, team_id=202).observed.pass_completion_pct == 0
    assert [m.match_id for m in player(result).matches] == [1001]


def test_counts_and_minutes_use_the_same_matches_when_timing_is_missing(metric_data):
    # Player 104 represents team 202 in both synthetic matches.
    path = metric_data / "events_Germany.json"
    events = json.loads(path.read_text())
    events[0]["eventSec"] = 44 * 60
    save_events(metric_data, events)
    result = run(
        metric_data,
        [
            action(8, 85, [1801], team=202, player=104),
            action(8, 85, [1802], match=1002, team=202, player=104),
        ],
    )
    row = player(result, 104, 202)

    assert row.observed.pass_attempts == 2
    assert row.observed.pass_completion_pct == 50
    assert row.rated.pass_attempts == 1
    assert row.rated.pass_completion_pct == 0
    assert row.rated_minutes == 75
    assert row.per90["pass_attempts"] == pytest.approx(90 / 75)
    assert [m.minutes for m in row.matches] == [None, 75]
    assert any("completeness unknown" in w for w in row.matches[0].warnings)


def test_missing_match_events_are_unknown_counts_not_zero(metric_data):
    path = metric_data / "events_Germany.json"
    save_events(
        metric_data, [e for e in json.loads(path.read_text()) if e["matchId"] == 1002]
    )

    row = player(run(metric_data))

    assert row.observed is None
    assert row.rated is None
    assert row.rated_minutes is None
    assert row.matches[0].counts is None
    assert row.matches[0].minutes is None
    assert all(value is None for value in row.per90.values())


def test_unused_substitutes_excluded_and_non_appearance_events_have_no_rates(
    metric_data,
):
    result = run(metric_data, [action(8, 85, [1801], player=109)])
    row = player(result, 109)

    assert not row.matches[0].appearance_recorded
    assert row.observed.pass_attempts == 1
    assert row.rated_minutes is None
    assert len(result.non_appearance_event_ids) == 1
    assert all(value is None for value in row.per90.values())


def test_unused_bench_player_without_actions_is_not_an_appearance(metric_data):
    assert not any(p.player_id == 109 for p in run(metric_data).players)


def test_interception_does_not_require_a_pass_or_an_accuracy_tag(metric_data):
    row = player(run(metric_data, [action(7, 72, [1401])]))

    assert row.observed.interceptions == 1
    assert row.observed.pass_attempts == 0


def test_unknown_players_and_missing_metadata_are_reported(metric_data):
    result = run(
        metric_data,
        [
            action(8, 85, [1801], player=0),
            action(8, 85, [1801], player=999),
        ],
    )

    assert len(result.unknown_player_event_ids) == 5
    assert len(result.missing_player_metadata_event_ids) == 1
    assert len(result.non_appearance_event_ids) == 1
    assert not any(p.player_id == 0 for p in result.players)
    assert player(result, 999).observed.accurate_passes == 1
    assert player(result, 999).rated is None


def test_no_action_player_with_minutes_has_zero_counts(metric_data):
    row = player(run(metric_data))

    assert row.rated == MetricCounts()
    assert row.per90 == dict.fromkeys(row.per90, 0)
    assert row.rated.pass_completion_pct is None


@pytest.mark.parametrize("minutes", [None, 0, -1, float("nan"), float("inf"), True])
def test_nonpositive_or_unknown_denominators_never_produce_rates(minutes):
    assert all(v is None for v in MetricCounts(pass_attempts=1).per90(minutes).values())


def test_aggregation_is_a_ratio_of_sums_not_an_average_of_match_rates(metric_data):
    result = run(
        metric_data,
        [
            action(8, 85, [1801], team=202, player=104),
            action(8, 85, [1802], match=1002, team=202, player=104),
            action(8, 85, [1802], match=1002, team=202, player=104),
        ],
    )
    row = player(result, 104, 202)

    assert row.rated_minutes == 96 + 75
    assert row.rated.pass_completion_pct == pytest.approx(100 / 3)
    assert row.per90["pass_attempts"] == pytest.approx(3 * 90 / 171)


def test_zero_minute_appearance_does_not_contribute_events_to_rates(metric_data):
    path = metric_data / "matches_Germany.json"
    matches = json.loads(path.read_text())
    matches[0]["teamsData"]["201"]["formation"]["substitutions"][0]["minute"] = 94
    path.write_text(json.dumps(matches))

    row = player(run(metric_data, [action(8, 85, [1801], player=103)]), 103)

    assert row.matches[0].minutes == 0
    assert row.observed.pass_attempts == 1
    assert row.rated.pass_attempts == 0
    assert row.rated_minutes == 90  # Only the other match contributes.
    assert row.per90["pass_attempts"] == 0


def test_missing_metadata_does_not_discard_a_known_appearance(metric_data):
    path = metric_data / "players.json"
    path.write_text(
        json.dumps([p for p in json.loads(path.read_text()) if p["wyId"] != 101])
    )

    row = player(run(metric_data, [action(8, 85, [1801])]))

    assert row.rated_minutes == 96
    assert row.rated.pass_attempts == 1
    assert any("missing from players.json" in w for w in row.matches[0].warnings)
