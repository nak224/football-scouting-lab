"""Summarize locally supplied Wyscout metadata and optional events."""

import argparse
import sys
from collections import Counter
from pathlib import Path

from .wyscout import MetadataError, load_events, load_season


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="directory containing matches_Germany.json, players.json, and teams.json",
    )
    parser.add_argument(
        "--events",
        action="store_true",
        help="also load and summarize events_Germany.json from the same directory",
    )
    args = parser.parse_args(argv)
    try:
        season = load_season(args.data_dir)
        events = load_events(args.data_dir, season) if args.events else None
    except MetadataError as error:
        parser.exit(2, f"error: {error}\n")

    print("Wyscout Bundesliga 2017/18")
    print(f"Matches: {len(season.matches)}")
    print(f"Teams: {len(season.referenced_team_ids)}")
    print(
        f"Referenced players: {len(season.referenced_player_ids)} (includes unused bench)"
    )
    played = {row.player_id for row in season.participation if row.played}
    print(f"Players recorded as appearing: {len(played)}")
    if season.missing_player_ids:
        ids = ", ".join(map(str, sorted(season.missing_player_ids)))
        print(f"warning: player IDs missing from players.json: {ids}", file=sys.stderr)
    if events is not None:
        print(f"Events: {len(events.records)}")
        print(f"Matches with events: {len(events.match_ids)} / {len(season.matches)}")
        for label, field in (
            ("Event types", "eventId"),
            ("Match periods", "matchPeriod"),
        ):
            counts = Counter(event[field] for event in events.records.values())
            summary = ", ".join(
                f"{key}={count}" for key, count in sorted(counts.items())
            )
            print(f"{label}: {summary}")
        for event_ids, description in (
            (events.unknown_player_event_ids, "have unknown playerId 0"),
            (
                events.missing_player_metadata_event_ids,
                "reference missing player metadata",
            ),
            (
                events.unlisted_player_event_ids,
                "reference players outside the match-team squad",
            ),
        ):
            if event_ids:
                print(
                    f"warning: {len(event_ids)} events {description}", file=sys.stderr
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
