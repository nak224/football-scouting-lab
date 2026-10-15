"""Combined replacement demo using the unchanged four-player reviewed cohort."""

import argparse
from collections import Counter
from pathlib import Path
from time import perf_counter

from midfield_roles import DEMO_REVIEWS

from football_scouting_lab.metrics import calculate_metrics
from football_scouting_lab.recruitment import rank_replacements
from football_scouting_lab.roles import ROLE_TEMPLATES, EligibilityThresholds
from football_scouting_lab.wyscout import MetadataError, load_events, load_season


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--reference-player", type=int, default=224677)
    parser.add_argument("--reference-team", type=int, default=2447)
    parser.add_argument(
        "--role", choices=ROLE_TEMPLATES, default="deep_lying_playmaker"
    )
    parser.add_argument("--style-priority", type=float, default=0.5)
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
        result = rank_replacements(
            metrics.players,
            reviews,
            (args.reference_player, args.reference_team),
            args.role,
            style_priority=args.style_priority,
            thresholds=thresholds,
            limit=args.limit,
        )
        ranked = perf_counter()
    except (MetadataError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print("Replacement ranking: limited four-player positional-proxy demonstration.")
    print(f"Loaded: {len(metadata.matches)} matches, {metrics.event_count} events")
    print(f"Reference: {result.reference_id}; role: {result.role.role}")
    print(
        f"Style priority: {result.style_priority}; role priority: {1 - result.style_priority}"
    )
    print(
        f"Style cohort: {result.style.normalization_ids}; weights: {result.style.weights}"
    )
    print(f"Role cohort: {result.role.reference_ids}; weights: {result.role.weights}")
    print(f"Style normalization ranges: {result.style.feature_ranges}")
    reference = result.style.reference
    print(
        f"Reference sample: minutes={reference.player.rated_minutes:.2f} "
        f"rated/appearances={reference.rated_matches}/{reference.recorded_appearances} "
        f"coverage={reference.appearance_coverage:.2%}"
    )
    reasons = Counter(reason for row in result.candidates for reason in row.reasons)
    print(f"Exclusion reasons (may overlap): {dict(sorted(reasons.items()))}")
    print(f"Unknown-player events: {len(metrics.unknown_player_event_ids)}")
    print(
        f"Events without recorded appearances: {len(metrics.non_appearance_event_ids)}"
    )
    for warning in (*result.style.warnings, *result.warnings):
        print(f"warning: {warning}")
    print(f"Combined shortlist: {len(result.shortlist)} entries")
    for row in result.shortlist:
        sample = row.style.candidate
        print(
            f"player={row.candidate_id[0]} team={row.candidate_id[1]} "
            f"style={row.style.score:.4f} role={row.role.score:.4f} "
            f"combined={row.combined_score:.4f} "
            f"style_points={row.style_contribution:.4f} role_points={row.role_contribution:.4f} "
            f"minutes={sample.player.rated_minutes:.2f} "
            f"rated/appearances={sample.rated_matches}/{sample.recorded_appearances} "
            f"coverage={sample.appearance_coverage:.2%}"
        )
        print(f"  Style explanations: {row.style.differences}")
        print(f"  Role explanations: {row.role.contributions}")
    print(
        "Source scores, samples and timing warnings are preserved in the returned results."
    )
    print(
        f"Runtime seconds: load={loaded - started:.6f} metrics={calculated - loaded:.6f} "
        f"ranking={ranked - calculated:.6f} total={ranked - started:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
