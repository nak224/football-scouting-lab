"""Local-data demonstration using four explicitly reviewed positional-proxy entries.

This is a limited demonstration cohort, not verified match-by-match positions.
See docs/roles.md for the manual identity review, evidence and limitations.
"""

import argparse
from collections import Counter
from pathlib import Path

from football_scouting_lab.demo_cohort import DEMO_REVIEWS
from football_scouting_lab.demo_cohort import EVIDENCE as EVIDENCE
from football_scouting_lab.metrics import calculate_metrics
from football_scouting_lab.roles import (
    ROLE_TEMPLATES,
    EligibilityThresholds,
    score_role,
)
from football_scouting_lab.wyscout import MetadataError, load_events, load_season


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--min-rated-minutes", type=float, default=600)
    parser.add_argument("--min-appearance-coverage", type=float, default=0.6)
    args = parser.parse_args(argv)
    try:
        thresholds = EligibilityThresholds(
            args.min_rated_minutes, args.min_appearance_coverage
        )
        metadata = load_season(args.data_dir)
        events = load_events(args.data_dir, metadata)
        metrics = calculate_metrics(metadata, events)
    except (MetadataError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    keys = {(p.player_id, p.team_id) for p in metrics.players}
    reviews = {key: review for key, review in DEMO_REVIEWS.items() if key in keys}
    print("Demo cohort: secondary positional proxies, not match-position truth.")
    print(f"Loaded: {len(metadata.matches)} matches, {metrics.event_count} events")
    print(f"Demo reviews present: {len(reviews)} / {len(DEMO_REVIEWS)}")
    print(f"Unknown-player events: {len(metrics.unknown_player_event_ids)}")
    print(
        f"Events without recorded appearances: {len(metrics.non_appearance_event_ids)}"
    )
    print("Timing warnings remain in each candidate's player-match metrics.")
    for role in ROLE_TEMPLATES:
        result = score_role(metrics.players, reviews, role, thresholds=thresholds)
        display_weights = {
            name: round(weight, 4) for name, weight in result.weights.items()
        }
        print(
            f"\n{role}: reference size {len(result.reference_ids)}; weights {display_weights}"
        )
        reasons = Counter(reason for row in result.candidates for reason in row.reasons)
        print(f"Exclusion reasons (may overlap): {dict(sorted(reasons.items()))}")
        for row in result.candidates:
            candidate = row.eligibility
            player = candidate.player
            if candidate.review.status == "unverified":
                continue
            name = metadata.players.get(player.player_id, {}).get(
                "shortName", "unknown"
            )
            score = f"{row.score:.2f}" if row.score is not None else "unavailable"
            minutes = (
                f"{player.rated_minutes:.2f}"
                if player.rated_minutes is not None
                else "unknown"
            )
            coverage = (
                f"{candidate.appearance_coverage:.2%}"
                if candidate.appearance_coverage is not None
                else "unknown"
            )
            print(
                f"{name} player={player.player_id} team={player.team_id} "
                f"score={score} minutes={minutes} "
                f"rated/appearances={candidate.rated_matches}/{candidate.recorded_appearances} "
                f"coverage={coverage} reasons={row.reasons}"
            )
            for part in row.contributions:
                print(
                    f"  {part.metric}: raw={part.measurement:.4f}, "
                    f"percentile={part.percentile:.4f}, weight={part.weight:.4f}, "
                    f"points={part.points:.4f}"
                )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
