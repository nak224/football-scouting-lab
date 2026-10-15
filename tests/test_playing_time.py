import json

import pytest

from football_scouting_lab.playing_time import estimate_playing_time
from football_scouting_lab.wyscout import MetadataError, load_events, load_season


def rewrite(data_dir, filename, edit):
    path = data_dir / filename
    records = json.loads(path.read_text())
    edit(records)
    path.write_text(json.dumps(records))


@pytest.fixture
def timed_data(synthetic_data_dir):
    """Fictional 47/49-minute halves, not a copied football match."""

    def prepare(matches):
        for match in matches:
            match["duration"] = "Regular"
            for team in match["teamsData"].values():
                for field in ("lineup", "bench"):
                    for player in team["formation"][field]:
                        player["redCards"] = "0"

    rewrite(synthetic_data_dir, "matches_Germany.json", prepare)

    def endpoints(events):
        events[0]["eventSec"] = 47 * 60
        events[2].update(matchPeriod="2H", eventSec=49 * 60)

    rewrite(synthetic_data_dir, "events_Germany.json", endpoints)
    return synthetic_data_dir


def estimate(data_dir, *, with_events=True):
    metadata = load_season(data_dir)
    events = load_events(data_dir, metadata) if with_events else None
    return estimate_playing_time(metadata, 1001, events)


def player(result, player_id):
    return next(row for row in result.players if row.player_id == player_id)


def set_substitution(data_dir, minute):
    rewrite(
        data_dir,
        "matches_Germany.json",
        lambda matches: matches[0]["teamsData"]["201"]["formation"]["substitutions"][
            0
        ].update(minute=minute),
    )


def set_card(data_dir, player_id, value):
    def edit(matches):
        formation = matches[0]["teamsData"]["201"]["formation"]
        for entry in formation["lineup"] + formation["bench"]:
            if entry["playerId"] == player_id:
                entry["redCards"] = value

    rewrite(data_dir, "matches_Germany.json", edit)


def tagged_dismissal(data_dir, player_id, period, seconds):
    rewrite(
        data_dir,
        "events_Germany.json",
        lambda events: events[3].update(
            playerId=player_id,
            matchPeriod=period,
            eventSec=seconds,
            tags=[{"id": 1703}],
        ),
    )


def test_full_match_keeps_identity_and_includes_observed_stoppage(timed_data):
    result = estimate(timed_data)

    assert result.period_minutes == {"1H": 47, "2H": 49}
    assert result.duration_minutes == 96
    assert player(result, 101).minutes == 96
    assert (
        player(result, 101).match_id,
        player(result, 101).team_id,
        player(result, 101).player_id,
    ) == (1001, 201, 101)
    assert any(
        "not an official final whistle" in warning for warning in result.warnings
    )


@pytest.mark.parametrize("minute", [45, 46])
def test_halftime_substitution_uses_observed_first_half_boundary(timed_data, minute):
    set_substitution(timed_data, minute)

    result = estimate(timed_data)

    assert player(result, 102).minutes == 47
    assert player(result, 103).minutes == 49
    assert any("halftime" in warning for warning in player(result, 103).warnings)


def test_second_half_substitution_uses_nominal_clock_plus_first_half_stoppage(
    timed_data,
):
    result = estimate(timed_data)

    assert player(result, 102).minutes == 62
    assert player(result, 103).minutes == 34


def test_first_half_and_second_half_stoppage_substitutions(timed_data):
    set_substitution(timed_data, 30)
    result = estimate(timed_data)
    assert player(result, 102).minutes == 30
    assert player(result, 103).minutes == 66

    set_substitution(timed_data, 92)
    result = estimate(timed_data)
    assert player(result, 102).minutes == 94
    assert player(result, 103).minutes == 2


def test_unused_bench_players_are_excluded(timed_data):
    result = estimate(timed_data)

    assert {row.player_id for row in result.players} == {101, 102, 103, 104, 105}
    assert 106 not in {row.player_id for row in result.players}
    assert 109 not in {row.player_id for row in result.players}


@pytest.mark.parametrize(
    ("period", "seconds", "card", "expected"),
    [
        ("1H", 30 * 60, "30", 30),
        ("2H", 21 * 60, "66", 68),
        ("1H", 47 * 60, "47", 47),
    ],
)
def test_dismissal_uses_tagged_period_timestamp(
    timed_data, period, seconds, card, expected
):
    set_card(timed_data, 101, card)
    tagged_dismissal(timed_data, 101, period, seconds)

    assert player(estimate(timed_data), 101).minutes == expected


def test_dismissal_can_fall_back_to_documented_redcards_clock(timed_data):
    set_card(timed_data, 101, "71")

    row = player(estimate(timed_data), 101)

    assert row.minutes == 73
    assert any("nominal redCards clock" in warning for warning in row.warnings)


def test_tagged_dismissal_conflicting_with_zero_card_is_used_and_flagged(timed_data):
    tagged_dismissal(timed_data, 101, "1H", 30 * 60)

    row = player(estimate(timed_data), 101)

    assert row.minutes == 30
    assert any("conflicts" in warning for warning in row.warnings)


def test_off_pitch_card_does_not_shorten_an_already_completed_interval(timed_data):
    set_card(timed_data, 102, "80")
    tagged_dismissal(timed_data, 102, "2H", 35 * 60)

    row = player(estimate(timed_data), 102)

    assert row.minutes == 62
    assert any("off-pitch" in warning for warning in row.warnings)


def test_dismissal_before_entry_has_no_estimate(timed_data):
    set_card(timed_data, 103, "20")
    tagged_dismissal(timed_data, 103, "1H", 20 * 60)

    row = player(estimate(timed_data), 103)

    assert row.minutes is None
    assert any("precedes entry" in warning for warning in row.warnings)


def test_distinct_dismissal_timestamps_are_ambiguous(timed_data):
    tagged_dismissal(timed_data, 101, "1H", 30 * 60)
    rewrite(
        timed_data,
        "events_Germany.json",
        lambda events: events[4].update(
            playerId=101, matchPeriod="1H", eventSec=32 * 60, tags=[{"id": 1701}]
        ),
    )

    row = player(estimate(timed_data), 101)

    assert row.minutes is None
    assert any("multiple distinct" in warning for warning in row.warnings)


@pytest.mark.parametrize("bad_minute", [None, -1, 120, "45+2", True, float("nan")])
def test_invalid_substitution_time_leaves_affected_players_unknown(
    timed_data, bad_minute
):
    set_substitution(timed_data, bad_minute)

    result = estimate(timed_data)

    assert player(result, 102).minutes is None
    assert player(result, 103).minutes is None
    assert player(result, 101).minutes == 96
    assert player(result, 102).warnings


def test_ambiguous_first_half_stoppage_clock_is_not_guessed(timed_data):
    set_substitution(timed_data, 47)

    row = player(estimate(timed_data), 103)

    assert row.minutes is None
    assert any("overlaps" in warning for warning in row.warnings)


def test_reversed_substitution_times_are_not_clamped(timed_data):
    rewrite(
        timed_data,
        "matches_Germany.json",
        lambda matches: matches[0]["teamsData"]["201"]["formation"][
            "substitutions"
        ].append({"playerIn": 109, "playerOut": 103, "minute": 55}),
    )

    result = estimate(timed_data)

    assert player(result, 103).minutes is None
    assert player(result, 109).minutes is None
    assert any("list order" in warning for warning in player(result, 109).warnings)


def test_no_events_does_not_assume_ninety_minutes(timed_data):
    result = estimate(timed_data, with_events=False)

    assert result.duration_minutes is None
    assert all(row.minutes is None for row in result.players)
    assert any("endpoint missing" in warning for warning in result.warnings)


@pytest.mark.parametrize("missing_period", ["1H", "2H"])
def test_missing_period_leaves_minutes_unknown(timed_data, missing_period):
    rewrite(
        timed_data,
        "events_Germany.json",
        lambda events: events.__setitem__(
            slice(None),
            [
                e
                for e in events
                if not (e["matchId"] == 1001 and e["matchPeriod"] == missing_period)
            ],
        ),
    )

    result = estimate(timed_data)

    assert result.period_minutes[missing_period] is None
    assert result.duration_minutes is None
    assert all(row.minutes is None for row in result.players)


def test_early_period_endpoint_is_flagged_as_incomplete(timed_data):
    rewrite(
        timed_data,
        "events_Germany.json",
        lambda events: events[2].update(eventSec=20 * 60),
    )

    result = estimate(timed_data)

    assert result.period_minutes["2H"] == 20
    assert result.duration_minutes is None
    assert all(row.minutes is None for row in result.players)


def test_invalid_dismissal_metadata_has_no_estimate(timed_data):
    set_card(timed_data, 101, "unknown")

    row = player(estimate(timed_data), 101)

    assert row.minutes is None
    assert any("missing/invalid" in warning for warning in row.warnings)


def test_invalid_event_timestamp_invalidates_duration_instead_of_being_ignored(
    timed_data,
):
    metadata = load_season(timed_data)
    events = load_events(timed_data, metadata)
    events.records[5001]["eventSec"] = float("nan")

    result = estimate_playing_time(metadata, 1001, events)

    assert result.duration_minutes is None
    assert all(row.minutes is None for row in result.players)
    assert any("invalid event timestamp" in warning for warning in result.warnings)


def test_unsupported_extra_period_is_not_silently_excluded(timed_data):
    rewrite(
        timed_data,
        "events_Germany.json",
        lambda events: events[3].update(matchPeriod="E1", eventSec=15 * 60),
    )

    result = estimate(timed_data)

    assert result.duration_minutes is None
    assert any("unsupported period" in warning for warning in result.warnings)


def test_unknown_match_has_a_clear_error(timed_data):
    with pytest.raises(MetadataError, match="missing from loaded matches"):
        estimate_playing_time(load_season(timed_data), 999)
