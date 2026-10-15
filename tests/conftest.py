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
