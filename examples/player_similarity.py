"""Local style shortlist using the unchanged four-player demonstration cohort."""

import argparse
from collections import Counter
from pathlib import Path
from time import perf_counter

from midfield_roles import DEMO_REVIEWS

from football_scouting_lab.metrics import calculate_metrics
from football_scouting_lab.roles import EligibilityThresholds
from football_scouting_lab.similarity import compare_styles, replacement_shortlist
from football_scouting_lab.wyscout import MetadataError, load_events, load_season


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--reference-player", type=int, default=224677)
    parser.add_argument("--reference-team", type=int, default=2447)
    parser.add_argument("--min-rated-minutes", type=float, default=600)
    parser.add_argument("--min-appearance-coverage", type=float, default=0.6)
    parser.add_argument("--limit", type=int, default=3)
    args = parser.parse_args(argv)
    started = perf_counter()
    try:
        thresholds = EligibilityThresholds(
            args.min_rated_minutes, args.min_appearance_coverage
        )
        metadata = load_season(args.data_dir)
        events = load_events(args.data_dir, metadata)
        loaded = perf_counter()
        metrics = calculate_metrics(metadata, events)
        calculated = perf_counter()
        keys = {(p.player_id, p.team_id) for p in metrics.players}
        reviews = {key: review for key, review in DEMO_REVIEWS.items() if key in keys}
        result = compare_styles(
            metrics.players,
            reviews,
            (args.reference_player, args.reference_team),
            thresholds=thresholds,
        )
        shortlist = replacement_shortlist(result, limit=args.limit)
        compared = perf_counter()
    except (MetadataError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print("Style similarity: limited four-player positional-proxy demonstration.")
    print(f"Loaded: {len(metadata.matches)} matches, {metrics.event_count} events")
    print(f"Unknown-player events: {len(metrics.unknown_player_event_ids)}")
    print(
        f"Events without recorded appearances: {len(metrics.non_appearance_event_ids)}"
    )
    reference = result.reference
    print(
        f"Reference: player={reference.player.player_id} team={reference.player.team_id} "
        f"minutes={reference.player.rated_minutes:.2f} "
        f"rated/appearances={reference.rated_matches}/{reference.recorded_appearances} "
        f"coverage={reference.appearance_coverage:.2%}"
    )
    print(
        f"Normalization cohort: {result.normalization_ids}; ranges: {result.feature_ranges}"
    )
    reasons = Counter(reason for row in result.candidates for reason in row.reasons)
    print(f"Exclusions (may overlap): {dict(sorted(reasons.items()))}")
    for warning in result.warnings:
        print(f"warning: {warning}")
    print(f"Replacement shortlist: {len(shortlist)} entries")
    for row in shortlist:
        candidate = row.candidate
        print(
            f"player={row.candidate_id[0]} team={row.candidate_id[1]} "
            f"similarity={row.score:.4f} distance={row.distance:.6f} "
            f"minutes={candidate.player.rated_minutes:.2f} "
            f"rated/appearances={candidate.rated_matches}/{candidate.recorded_appearances} "
            f"coverage={candidate.appearance_coverage:.2%}"
        )
        for part in row.differences:
            print(
                f"  {part.metric}: reference={part.reference_value:.4f} "
                f"candidate={part.candidate_value:.4f} difference={part.raw_difference:.4f} "
                f"normalized_difference={part.normalized_difference:.6f} "
                f"weight={part.weight:.4f} distance_contribution={part.contribution:.6f}"
            )
    print("Timing/source warnings remain in the returned player-match metrics.")
    print(
        f"Runtime seconds: load={loaded - started:.6f} metrics={calculated - loaded:.6f} "
        f"similarity_and_shortlist={compared - calculated:.6f} total={compared - started:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
