"""Deterministic, invented records for an offline portfolio demonstration.

No source records, real player/club identities or calculated scores are bundled.
Competition/season IDs only satisfy the existing loader's format contract.
"""

import json
from pathlib import Path

from .roles import PositionReview
from .wyscout import COMPETITION_ID, SEASON_ID

VERSION = "fictional-portfolio-v1"
BASELINE = ((910001, 99001), (910003, 99002), (910004, 99003))
CANDIDATE = (910002, 99001)
# ID, invented name, invented team, passes, accurate passes, interceptions, duel wins per appearance.
PROFILES = (
    (910001, "FICTIONAL Avery Vale", 99001, 48, 42, 1, 0),
    (910002, "FICTIONAL Blair Reed", 99001, 32, 24, 4, 3),
    (910003, "FICTIONAL Casey North", 99002, 36, 33, 2, 1),
    (910004, "FICTIONAL Drew West", 99003, 40, 34, 3, 2),
)
REVIEWS = {
    (player, team): PositionReview(
        "included",
        f"fictional:{VERSION}",
        "Assigned midfielder in a generated FICTIONAL fixture; no real position evidence.",
    )
    for player, _, team, *_ in PROFILES
}


def write_fictional_data(directory: str | Path) -> Path:
    """Write four new local JSON files. Never overwrite existing dataset files."""
    root = Path(directory)
    payloads = {
        "players.json": [
            {"wyId": player, "shortName": name, "role": {"name": "Midfielder"}}
            for player, name, *_ in PROFILES
        ],
        "teams.json": [
            {"wyId": team, "name": name}
            for team, name in (
                (99001, "FICTIONAL Harbor FC"),
                (99002, "FICTIONAL Ridge FC"),
                (99003, "FICTIONAL Forest FC"),
            )
        ],
        "matches_Germany.json": [],
        "events_Germany.json": [],
    }
    root.mkdir(parents=True, exist_ok=True)
    if any((root / name).exists() for name in payloads):
        raise FileExistsError(
            "Fictional generator requires a directory without existing dataset files"
        )
    matches, events = payloads["matches_Germany.json"], payloads["events_Germany.json"]
    for number in range(14):
        match_id = 920001 + number
        away_team = 99002 if number < 7 else 99003
        squads = {
            team: [profile for profile in PROFILES if profile[2] == team]
            for team in (99001, away_team)
        }
        matches.append(
            {
                "wyId": match_id,
                "competitionId": COMPETITION_ID,
                "seasonId": SEASON_ID,
                "duration": "Regular",
                "fictionalDemo": VERSION,
                "teamsData": {
                    str(team): {
                        "teamId": team,
                        "side": "home" if team == 99001 else "away",
                        "formation": {
                            "lineup": [
                                {"playerId": profile[0], "redCards": "0"}
                                for profile in squad
                            ],
                            "bench": [],
                            "substitutions": [],
                        },
                    }
                    for team, squad in squads.items()
                },
            }
        )

        def append_event(
            player, team, family, subtype, tags, *, period="1H", seconds=None
        ):
            events.append(
                {
                    "id": 930001 + len(events),
                    "matchId": match_id,
                    "teamId": team,
                    "playerId": player,
                    "eventId": family,
                    "eventName": "FICTIONAL event",
                    "subEventId": subtype,
                    "subEventName": "FICTIONAL subtype",
                    "tags": [{"id": tag} for tag in tags],
                    "positions": [],
                    "matchPeriod": period,
                    "eventSec": seconds
                    if seconds is not None
                    else 60 + len(events) % 2400,
                }
            )

        # Invented period endpoints exercise the estimator, not official final whistles.
        for period, seconds in (("1H", 47 * 60), ("2H", 49 * 60)):
            append_event(0, 99001, 7, "", [], period=period, seconds=seconds)
        for team, squad in squads.items():
            for player, _, _, passes, accurate, interceptions, wins in squad:
                for attempt in range(passes):
                    append_event(
                        player, team, 8, 85, [1801 if attempt < accurate else 1802]
                    )
                for _ in range(interceptions):
                    append_event(player, team, 7, "", [1401])
                for _ in range(wins):
                    append_event(player, team, 1, 12, [703])
    for name, records in payloads.items():
        with (root / name).open("x", encoding="utf-8") as stream:
            json.dump(records, stream, ensure_ascii=False, sort_keys=True)
    return root
