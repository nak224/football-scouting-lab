"""Summarize locally supplied Wyscout match metadata."""

import argparse
import sys
from pathlib import Path

from .wyscout import MetadataError, load_season


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--data-dir",
        type=Path,
        required=True,
        help="directory containing matches_Germany.json, players.json, and teams.json",
    )
    args = parser.parse_args(argv)
    try:
        season = load_season(args.data_dir)
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
