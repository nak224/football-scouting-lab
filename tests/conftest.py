from pathlib import Path
from shutil import copytree

import pytest


@pytest.fixture
def synthetic_data_dir(tmp_path):
    """Copy hand-authored fictional records; never use external data in tests."""
    source = Path(__file__).parent / "fixtures" / "wyscout"
    return copytree(source, tmp_path / "wyscout")


@pytest.fixture
def ui_data_dir(synthetic_data_dir):
    """Two fictional matches with complete periods; no actual football records."""
    import json

    matches_path = synthetic_data_dir / "matches_Germany.json"
    matches = json.loads(matches_path.read_text())
    for match in matches:
        match["duration"] = "Regular"
        for team in match["teamsData"].values():
            formation = team["formation"]
            for player in formation["lineup"] + formation["bench"]:
                player["redCards"] = "0"
    matches_path.write_text(json.dumps(matches))
    events = []
    for match_id in (1001, 1002):
        for period, seconds in (("1H", 47 * 60), ("2H", 49 * 60)):
            events.append(
                {
                    "id": len(events) + 1,
                    "matchId": match_id,
                    "teamId": 201,
                    "playerId": 0,
                    "eventId": 7,
                    "eventName": "Others on the ball",
                    "subEventName": "",
                    "subEventId": "",
                    "tags": [],
                    "positions": [],
                    "matchPeriod": period,
                    "eventSec": seconds,
                }
            )
        for player_id, team_id, accurate in (
            (101, 201 if match_id == 1001 else 202, True),
            (104, 202, False),
        ):
            events.append(
                {
                    "id": len(events) + 1,
                    "matchId": match_id,
                    "teamId": team_id,
                    "playerId": player_id,
                    "eventId": 8,
                    "eventName": "Pass",
                    "subEventName": "Simple pass",
                    "subEventId": 85,
                    "tags": [{"id": 1801 if accurate else 1802}],
                    "positions": [],
                    "matchPeriod": "1H",
                    "eventSec": 60,
                }
            )
    (synthetic_data_dir / "events_Germany.json").write_text(json.dumps(events))
    return synthetic_data_dir


@pytest.fixture
def ui_demo_reviews(monkeypatch):
    """Replace production reviews only inside tests with explicit fictional reviews."""
    from football_scouting_lab import ui_data
    from football_scouting_lab.roles import PositionReview

    review = PositionReview("included", "synthetic:test", "Fictional midfielder")
    reviews = {(101, 201): review, (101, 202): review, (104, 202): review}
    monkeypatch.setattr(ui_data, "DEMO_REVIEWS", reviews)
    return reviews


@pytest.fixture
def midfield_data_dir(tmp_path):
    """Entirely fictional records; IDs match UI defaults only to test selections.

    Names, match sheets, events and all measurements are hand-authored here.
    These are not actual Bundesliga matches, metrics or position annotations.
    """
    import json

    directory = tmp_path / "fictional-midfield"
    directory.mkdir()
    players = [
        {"wyId": 3345, "shortName": "Fictional Thiago"},
        {"wyId": 20475, "shortName": "Fictional Vidal"},
        {"wyId": 224677, "shortName": "Fictional Weigl"},
        {"wyId": 289711, "shortName": "Fictional Keita"},
    ]
    teams = [
        {"wyId": key, "name": name}
        for key, name in (
            (2444, "Fictional Bayern"),
            (2447, "Fictional Dortmund"),
            (2975, "Fictional Leipzig"),
        )
    ]
    matches, events = [], []
    for match_id in range(1001, 1015):
        away_team, away_player = (2447, 224677) if match_id < 1008 else (2975, 289711)
        squads = {2444: (3345, 20475), away_team: (away_player,)}
        matches.append(
            {
                "wyId": match_id,
                "competitionId": 426,
                "seasonId": 181137,
                "duration": "Regular",
                "teamsData": {
                    str(team): {
                        "teamId": team,
                        "side": "home" if team == 2444 else "away",
                        "formation": {
                            "lineup": [
                                {"playerId": player, "redCards": "0"}
                                for player in squad
                            ],
                            "bench": [],
                            "substitutions": [],
                        },
                    }
                    for team, squad in squads.items()
                },
            }
        )

        def event(player, team, family, subtype, tags, *, period="1H", seconds=60):
            return {
                "id": len(events) + 1,
                "matchId": match_id,
                "teamId": team,
                "playerId": player,
                "eventId": family,
                "eventName": "Fictional event",
                "subEventId": subtype,
                "subEventName": "Fictional subtype",
                "tags": [{"id": tag} for tag in tags],
                "positions": [],
                "matchPeriod": period,
                "eventSec": seconds,
            }

        for period, seconds in (("1H", 47 * 60), ("2H", 49 * 60)):
            events.append(event(0, 2444, 7, "", [], period=period, seconds=seconds))
        for team, squad in squads.items():
            for player in squad:
                outcomes = {
                    3345: (1801, 1801, 1801),
                    20475: (1801, 1802),
                    224677: (1801,),
                    289711: (1801, 1801),
                }[player]
                for outcome in outcomes:
                    events.append(event(player, team, 8, 85, [outcome]))
                for _ in range({3345: 0, 20475: 2, 224677: 1, 289711: 1}[player]):
                    events.append(event(player, team, 1, 12, [1401, 703]))
    for filename, records in (
        ("matches_Germany.json", matches),
        ("players.json", players),
        ("teams.json", teams),
        ("events_Germany.json", events),
    ):
        (directory / filename).write_text(json.dumps(records))
    return directory
