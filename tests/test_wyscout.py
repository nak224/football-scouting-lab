import json

import pytest

from football_scouting_lab.wyscout import MetadataError, load_season


def rewrite(data_dir, filename, edit):
    path = data_dir / filename
    records = json.loads(path.read_text())
    edit(records)
    path.write_text(json.dumps(records))


def first_formation(records):
    return records[0]["teamsData"]["201"]["formation"]


def test_preserves_records_and_historical_affiliation(synthetic_data_dir):
    season = load_season(synthetic_data_dir)

    assert set(season.matches) == {1001, 1002}
    assert season.referenced_team_ids == {201, 202}
    assert season.referenced_player_ids == {101, 102, 103, 104, 105, 106, 109}
    assert season.players[101]["currentTeamId"] == 9999
    assert {
        (row.match_id, row.team_id)
        for row in season.participation
        if row.player_id == 101
    } == {
        (1001, 201),
        (1002, 202),
    }
    for filename, indexed in (
        ("matches_Germany.json", season.matches),
        ("players.json", season.players),
        ("teams.json", season.teams),
    ):
        original = json.loads((synthetic_data_dir / filename).read_text())
        assert list(indexed.values()) == original
    assert not season.missing_player_ids


def test_bench_listing_is_distinct_from_appearance(synthetic_data_dir):
    season = load_season(synthetic_data_dir)
    rows = {
        row.player_id: row
        for row in season.participation
        if row.match_id == 1001 and row.team_id == 201
    }

    assert rows[101].started and rows[101].played
    assert rows[102].started and rows[102].substituted_out and rows[102].played
    assert rows[103].on_bench and rows[103].substituted_in and rows[103].played
    assert not rows[103].started
    assert rows[109].on_bench and not rows[109].played


def test_missing_player_metadata_remains_explicit(synthetic_data_dir):
    rewrite(synthetic_data_dir, "players.json", lambda rows: rows.pop(0))

    season = load_season(synthetic_data_dir)

    assert season.missing_player_ids == {101}
    assert 101 not in season.players
    assert {
        (row.match_id, row.team_id)
        for row in season.participation
        if row.player_id == 101
    } == {
        (1001, 201),
        (1002, 202),
    }


@pytest.mark.parametrize(
    "filename", ["matches_Germany.json", "players.json", "teams.json"]
)
def test_missing_file_names_the_required_file(synthetic_data_dir, filename):
    (synthetic_data_dir / filename).unlink()

    with pytest.raises(MetadataError, match=filename):
        load_season(synthetic_data_dir)


@pytest.mark.parametrize("content", [b"not JSON", b"\xff"])
def test_unreadable_json_has_a_contextual_error(synthetic_data_dir, content):
    (synthetic_data_dir / "players.json").write_bytes(content)

    with pytest.raises(MetadataError, match="players.json: cannot read JSON"):
        load_season(synthetic_data_dir)


@pytest.mark.parametrize("content", [{}, None, "records", [], [42], [{}]])
def test_rejects_invalid_record_arrays(synthetic_data_dir, content):
    (synthetic_data_dir / "players.json").write_text(json.dumps(content))

    with pytest.raises(MetadataError, match="players.json"):
        load_season(synthetic_data_dir)


@pytest.mark.parametrize(
    "content",
    [
        '[{"wyId": 101, "wyId": 102}]',
        '[{"wyId": 101, "profile": {"name": "A", "name": "B"}}]',
    ],
)
def test_duplicate_json_keys_cannot_silently_overwrite_data(
    synthetic_data_dir, content
):
    (synthetic_data_dir / "players.json").write_text(content)

    with pytest.raises(MetadataError, match="players.json:.*duplicate JSON key"):
        load_season(synthetic_data_dir)


@pytest.mark.parametrize("bad_id", [True, False, 0, -1, 1.5, "101", None])
def test_ids_must_be_positive_integers(synthetic_data_dir, bad_id):
    rewrite(
        synthetic_data_dir,
        "players.json",
        lambda rows: rows[0].update(wyId=bad_id),
    )

    with pytest.raises(MetadataError, match="positive integer ID"):
        load_season(synthetic_data_dir)


@pytest.mark.parametrize(
    "filename", ["matches_Germany.json", "players.json", "teams.json"]
)
def test_duplicate_record_ids_are_rejected(synthetic_data_dir, filename):
    rewrite(synthetic_data_dir, filename, lambda rows: rows.append(rows[0]))

    with pytest.raises(MetadataError, match="duplicate wyId"):
        load_season(synthetic_data_dir)


@pytest.mark.parametrize("field", ["competitionId", "seasonId"])
def test_other_competitions_or_seasons_are_rejected(synthetic_data_dir, field):
    rewrite(
        synthetic_data_dir,
        "matches_Germany.json",
        lambda rows: rows[0].update({field: 1}),
    )

    with pytest.raises(MetadataError, match=field):
        load_season(synthetic_data_dir)


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (lambda rows: rows[0].pop("teamsData"), "teamsData"),
        (lambda rows: rows[0]["teamsData"].pop("202"), "exactly two teams"),
        (lambda rows: rows[0]["teamsData"].update({"201": []}), "JSON object"),
        (lambda rows: rows[0]["teamsData"]["201"].update(teamId=999), "key must match"),
        (lambda rows: rows[0]["teamsData"]["201"].update(side="away"), "one home"),
        (lambda rows: rows[0]["teamsData"]["201"].update(formation=[]), "JSON object"),
        (lambda rows: first_formation(rows).update(lineup={}), "JSON array"),
        (
            lambda rows: first_formation(rows).update(lineup=[]),
            "lineup must not be empty",
        ),
        (lambda rows: first_formation(rows).update(bench="null"), "JSON array"),
        (
            lambda rows: first_formation(rows).pop("substitutions"),
            "missing substitutions",
        ),
        (lambda rows: first_formation(rows).update(substitutions={}), "JSON array"),
        (
            lambda rows: first_formation(rows).update(substitutions=[None]),
            "JSON object",
        ),
        (
            lambda rows: first_formation(rows)["lineup"][0].update(playerId=True),
            "integer ID",
        ),
        (
            lambda rows: first_formation(rows)["substitutions"][0].update(
                playerIn=False
            ),
            "integer ID",
        ),
    ],
)
def test_nested_structures_and_ids_are_validated(synthetic_data_dir, edit, message):
    rewrite(synthetic_data_dir, "matches_Germany.json", edit)

    with pytest.raises(MetadataError, match=message):
        load_season(synthetic_data_dir)


def test_unknown_team_metadata_is_rejected(synthetic_data_dir):
    rewrite(synthetic_data_dir, "teams.json", lambda rows: rows.pop(0))

    with pytest.raises(MetadataError, match="teamId 201 missing from teams.json"):
        load_season(synthetic_data_dir)


@pytest.mark.parametrize(
    ("edit", "message"),
    [
        (
            lambda rows: first_formation(rows)["lineup"].append({"playerId": 101}),
            "duplicate playerId",
        ),
        (
            lambda rows: first_formation(rows)["bench"].append({"playerId": 101}),
            "disjoint",
        ),
        (
            lambda rows: rows[0]["teamsData"]["202"]["formation"]["bench"].append(
                {"playerId": 101}
            ),
            "both teams",
        ),
        (
            lambda rows: first_formation(rows)["substitutions"][0].update(playerIn=999),
            "unused bench",
        ),
        (
            lambda rows: first_formation(rows)["substitutions"][0].update(
                playerOut=109
            ),
            "active player",
        ),
        (
            lambda rows: first_formation(rows)["substitutions"].append(
                {"playerIn": 103, "playerOut": 101}
            ),
            "unused bench",
        ),
    ],
)
def test_inconsistent_match_sheets_are_rejected(synthetic_data_dir, edit, message):
    rewrite(synthetic_data_dir, "matches_Germany.json", edit)

    with pytest.raises(MetadataError, match=message):
        load_season(synthetic_data_dir)


def test_substitute_can_later_be_substituted_out_without_timing_logic(
    synthetic_data_dir,
):
    rewrite(
        synthetic_data_dir,
        "matches_Germany.json",
        lambda rows: first_formation(rows)["substitutions"].append(
            {"playerIn": 109, "playerOut": 103}
        ),
    )

    season = load_season(synthetic_data_dir)
    row = next(
        row
        for row in season.participation
        if row.match_id == 1001 and row.player_id == 103
    )
    assert row.substituted_in and row.substituted_out and row.played
