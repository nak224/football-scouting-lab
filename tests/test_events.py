import json

import pytest

from football_scouting_lab.wyscout import MetadataError, load_events, load_season


def rewrite_events(data_dir, edit):
    path = data_dir / "events_Germany.json"
    records = json.loads(path.read_text())
    edit(records)
    path.write_text(json.dumps(records))


def test_preserves_original_records_and_source_order(synthetic_data_dir):
    metadata = load_season(synthetic_data_dir)
    original = json.loads((synthetic_data_dir / "events_Germany.json").read_text())

    events = load_events(synthetic_data_dir, metadata)

    assert list(events.records) == [5001, 5002, 5003, 5004, 5005]
    assert list(events.records.values()) == original
    assert events.match_ids == {1001, 1002}
    assert events.records[5001]["tags"] == [{"id": 1801, "syntheticNote": "retained"}]
    assert events.records[5002]["eventSec"] == 0.0
    assert events.records[5003]["subEventId"] == ""
    assert metadata.players[101]["currentTeamId"] == 9999


def test_reports_unknown_missing_and_unlisted_players_without_dropping_events(
    synthetic_data_dir,
):
    events = load_events(synthetic_data_dir, load_season(synthetic_data_dir))

    assert len(events.records) == 5
    assert events.unknown_player_event_ids == {5003}
    assert events.missing_player_metadata_event_ids == {5004}
    assert events.unlisted_player_event_ids == {5004, 5005}
    # The same player is correctly associated with different historical teams.
    assert 5001 not in events.unlisted_player_event_ids
    assert 5002 not in events.unlisted_player_event_ids


def test_missing_player_metadata_can_still_have_a_valid_squad_reference(
    synthetic_data_dir,
):
    path = synthetic_data_dir / "players.json"
    players = json.loads(path.read_text())
    path.write_text(json.dumps([player for player in players if player["wyId"] != 101]))

    events = load_events(synthetic_data_dir, load_season(synthetic_data_dir))

    assert {5001, 5002} <= events.missing_player_metadata_event_ids
    assert not {5001, 5002} & events.unlisted_player_event_ids
    assert events.records[5001]["playerId"] == 101


def test_match_team_squad_includes_unused_bench_players_without_changing_appearances(
    synthetic_data_dir,
):
    rewrite_events(synthetic_data_dir, lambda rows: rows[0].update(playerId=109))
    metadata = load_season(synthetic_data_dir)

    events = load_events(synthetic_data_dir, metadata)

    assert 5001 not in events.unlisted_player_event_ids
    assert not any(row.played for row in metadata.participation if row.player_id == 109)


def test_event_file_is_required_only_by_event_loading(synthetic_data_dir):
    (synthetic_data_dir / "events_Germany.json").unlink()
    metadata = load_season(synthetic_data_dir)

    with pytest.raises(MetadataError, match="events_Germany.json"):
        load_events(synthetic_data_dir, metadata)


@pytest.mark.parametrize("content", [b"not JSON", b"\xff", b"{}", b"[]", b"[null]"])
def test_invalid_event_file_is_reported_with_context(synthetic_data_dir, content):
    (synthetic_data_dir / "events_Germany.json").write_bytes(content)

    with pytest.raises(MetadataError, match="events_Germany.json"):
        load_events(synthetic_data_dir, load_season(synthetic_data_dir))


def test_duplicate_event_ids_are_rejected_across_matches(synthetic_data_dir):
    rewrite_events(synthetic_data_dir, lambda rows: rows[1].update(id=5001))

    with pytest.raises(MetadataError, match="duplicate id 5001"):
        load_events(synthetic_data_dir, load_season(synthetic_data_dir))


def test_duplicate_json_keys_are_rejected(synthetic_data_dir):
    (synthetic_data_dir / "events_Germany.json").write_text(
        '[{"id": 5001, "id": 5002}]'
    )

    with pytest.raises(MetadataError, match="duplicate JSON key"):
        load_events(synthetic_data_dir, load_season(synthetic_data_dir))


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("matchId", 9999, "missing from loaded matches"),
        ("teamId", 9999, "missing from teams.json"),
        ("teamId", 203, "is not in match 1001"),
    ],
)
def test_match_and_team_references_are_checked(
    synthetic_data_dir, field, value, message
):
    rewrite_events(synthetic_data_dir, lambda rows: rows[0].update({field: value}))

    with pytest.raises(MetadataError, match=message):
        load_events(synthetic_data_dir, load_season(synthetic_data_dir))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("id", 0),
        ("id", True),
        ("matchId", "1001"),
        ("teamId", False),
        ("playerId", -1),
        ("playerId", "101"),
        ("playerId", None),
        ("playerId", True),
        ("eventId", 0),
        ("eventId", "8"),
        ("eventName", ""),
        ("eventName", "  "),
        ("subEventId", -1),
        ("subEventId", False),
        ("subEventId", None),
        ("subEventName", None),
        ("matchPeriod", "3H"),
        ("matchPeriod", None),
        ("eventSec", -0.01),
        ("eventSec", True),
        ("eventSec", "2.125"),
        ("eventSec", float("nan")),
        ("eventSec", float("inf")),
        ("tags", None),
        ("tags", [{"id": 0}]),
        ("tags", [{"id": True}]),
        ("tags", [1801]),
        ("positions", {}),
        ("positions", [None]),
        ("positions", [{"x": 1}]),
        ("positions", [{"x": True, "y": 50}]),
        ("positions", [{"x": 50, "y": float("inf")}]),
    ],
)
def test_invalid_consumed_fields_are_rejected(synthetic_data_dir, field, value):
    rewrite_events(synthetic_data_dir, lambda rows: rows[0].update({field: value}))

    with pytest.raises(MetadataError, match=field):
        load_events(synthetic_data_dir, load_season(synthetic_data_dir))


@pytest.mark.parametrize(
    "field",
    [
        "id",
        "matchId",
        "teamId",
        "playerId",
        "eventId",
        "eventName",
        "subEventId",
        "subEventName",
        "matchPeriod",
        "eventSec",
        "tags",
        "positions",
    ],
)
def test_consumed_fields_are_required(synthetic_data_dir, field):
    rewrite_events(synthetic_data_dir, lambda rows: rows[0].pop(field))

    with pytest.raises(MetadataError, match=field):
        load_events(synthetic_data_dir, load_season(synthetic_data_dir))


@pytest.mark.parametrize("period", ["1H", "2H", "E1", "E2", "P"])
def test_periods_and_unsorted_timestamps_are_preserved(synthetic_data_dir, period):
    rewrite_events(
        synthetic_data_dir,
        lambda rows: rows[0].update(matchPeriod=period, eventSec=4000.125),
    )

    events = load_events(synthetic_data_dir, load_season(synthetic_data_dir))

    assert events.records[5001]["matchPeriod"] == period
    assert events.records[5001]["eventSec"] == 4000.125
    assert list(events.records)[0] == 5001


def test_unmapped_type_and_tag_ids_are_preserved(synthetic_data_dir):
    rewrite_events(
        synthetic_data_dir,
        lambda rows: rows[0].update(
            eventId=999, eventName="Synthetic new type", tags=[{"id": 99999}]
        ),
    )

    events = load_events(synthetic_data_dir, load_season(synthetic_data_dir))

    assert events.records[5001]["eventId"] == 999
    assert events.records[5001]["tags"] == [{"id": 99999}]


@pytest.mark.parametrize("point", [{"x": -1, "y": 50}, {"x": 50, "y": 100.1}])
def test_outside_coordinates_are_reported_without_clipping(synthetic_data_dir, point):
    rewrite_events(synthetic_data_dir, lambda rows: rows[0].update(positions=[point]))

    events = load_events(synthetic_data_dir, load_season(synthetic_data_dir))

    assert events.out_of_bounds_position_event_ids == {5001}
    assert events.records[5001]["positions"] == [point]
