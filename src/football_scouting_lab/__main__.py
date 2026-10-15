"""Summarize locally supplied Wyscout metadata and optional events."""

import argparse
import csv
import sys
from collections import Counter
from dataclasses import asdict, fields
from pathlib import Path

from .metrics import MetricCounts, SeasonMetrics, calculate_metrics
from .wyscout import MetadataError, load_events, load_season


def _write_metrics(path: Path, result: SeasonMetrics) -> None:
    """Empty CSV cells mean unknown, never an imputed zero."""
    rows = []
    for player in result.players:
        row = {"player_id": player.player_id, "team_id": player.team_id}
        for label, matches in (
            ("observed", player.matches),
            ("rated", [m for m in player.matches if m.rate_eligible]),
            ("unknown_minutes", [m for m in player.matches if m.minutes is None]),
            ("zero_minutes", [m for m in player.matches if m.minutes == 0]),
            ("missing_events", [m for m in player.matches if m.counts is None]),
        ):
            row[f"{label}_match_ids"] = ";".join(str(m.match_id) for m in matches)
            row[f"{label}_matches"] = len(matches)
        row["recorded_appearances"] = sum(m.appearance_recorded for m in player.matches)
        row["observed_player_events"] = sum(m.event_count for m in player.matches)
        row["rated_minutes"] = player.rated_minutes
        for label, counts in (("observed", player.observed), ("rated", player.rated)):
            values = asdict(counts) if counts else {}
            for field in fields(MetricCounts):
                row[f"{label}_{field.name}"] = values.get(field.name)
            row[f"{label}_pass_completion_pct"] = (
                counts.pass_completion_pct if counts else None
            )
        row.update({f"{name}_per90": value for name, value in player.per90.items()})
        row["warnings"] = " | ".join(
            dict.fromkeys(warning for m in player.matches for warning in m.warnings)
        )
        rows.append(row)
    with path.open("x", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _summarize_metrics(result: SeasonMetrics) -> None:
    usable = sum(match.duration_minutes is not None for match in result.matches)
    appearances = [
        m for p in result.players for m in p.matches if m.appearance_recorded
    ]
    positive = sum(m.rate_eligible for m in appearances)
    unknown = sum(m.minutes is None for m in appearances)
    zero = sum(m.minutes == 0 for m in appearances)
    print(f"Metrics: {len(result.players)} player-team rows")
    print(f"Usable match durations: {usable} / {len(result.matches)}")
    print(
        f"Appearing player-match coverage: {positive} positive, {unknown} unknown, "
        f"{zero} zero minutes / {len(appearances)}"
    )
    for match in result.matches:
        if match.duration_minutes is None:
            print(f"Excluded match {match.match_id}: {'; '.join(match.warnings)}")
    for event_ids, description in (
        (
            result.unknown_player_event_ids,
            "unknown-player events excluded from player metrics",
        ),
        (
            result.non_appearance_event_ids,
            "events without recorded appearances; no rates",
        ),
        (
            result.ambiguous_pass_event_ids,
            "passes with missing/conflicting outcome tags",
        ),
        (
            result.ambiguous_defensive_duel_event_ids,
            "defending duels with missing/conflicting outcome tags",
        ),
    ):
        print(f"Metric coverage: {len(event_ids)} {description}")
    print("Per-90 uses only matched positive-minute appearances; see docs/metrics.md.")


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
    parser.add_argument(
        "--metrics-csv",
        type=Path,
        help="export observed/matched player-team metrics to CSV; implies --events",
    )
    args = parser.parse_args(argv)
    try:
        season = load_season(args.data_dir)
        events = (
            load_events(args.data_dir, season)
            if args.events or args.metrics_csv is not None
            else None
        )
        metrics = None
        if args.metrics_csv is not None:
            metrics = calculate_metrics(season, events)
            _write_metrics(args.metrics_csv, metrics)
    except MetadataError as error:
        parser.exit(2, f"error: {error}\n")
    except OSError as error:
        parser.exit(2, f"error: cannot write metrics CSV: {error}\n")

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
            (
                events.out_of_bounds_position_event_ids,
                "have positions outside [0, 100]",
            ),
        ):
            if event_ids:
                print(
                    f"warning: {len(event_ids)} events {description}", file=sys.stderr
                )
    if metrics is not None:
        _summarize_metrics(metrics)
        print(f"Metrics CSV: {args.metrics_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
