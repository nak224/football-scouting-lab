"""Hypothetical midfield-trio demo; never an actual historical starting XI."""

import argparse
from pathlib import Path
from time import perf_counter

from football_scouting_lab.demo_cohort import DEMO_REVIEWS
from football_scouting_lab.metrics import calculate_metrics
from football_scouting_lab.roles import EligibilityThresholds, assess_eligibility
from football_scouting_lab.team_fit import compare_midfield
from football_scouting_lab.wyscout import load_events, load_season

# These players came from different clubs. Ordering is user choice, not observed slots.
BASELINE_LINEUP = ((3345, 2444), (224677, 2447), (289711, 2975))
CANDIDATE_ID = (20475, 2444)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--replacement-slot", type=int, choices=(0, 1, 2), default=2)
    parser.add_argument("--min-rated-minutes", type=float, default=600)
    parser.add_argument("--min-appearance-coverage", type=float, default=0.6)
    args = parser.parse_args(argv)
    started = perf_counter()
    try:
        thresholds = EligibilityThresholds(
            args.min_rated_minutes, args.min_appearance_coverage
        )
        metadata = load_season(args.data_dir)
        events = load_events(args.data_dir, metadata)
        metrics = calculate_metrics(metadata, events)
        calculated = perf_counter()
        cohort = tuple(
            row
            for row in metrics.players
            if (row.player_id, row.team_id) in DEMO_REVIEWS
        )
        if {(row.player_id, row.team_id) for row in cohort} != set(DEMO_REVIEWS):
            raise ValueError(
                "the fixed four-player demonstration cohort is not fully present in the local data"
            )
        eligibility = assess_eligibility(cohort, DEMO_REVIEWS, thresholds)
        excluded = [
            f"{(row.player.player_id, row.player.team_id)}: {'; '.join(row.reasons)}"
            for row in eligibility
            if not row.eligible
        ]
        if excluded:
            raise ValueError(
                "fixed demonstration cohort fails thresholds: " + " | ".join(excluded)
            )
        result = compare_midfield(
            cohort, BASELINE_LINEUP, args.replacement_slot, CANDIDATE_ID
        )
        compared = perf_counter()
    except (OSError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print("HYPOTHETICAL 4-3-3 midfield trio — not an actual historical starting XI.")
    print(
        "Four-player positional-proxy demonstration; players from different clubs are not assumed to have played together."
    )
    print(f"Loaded: {len(metadata.matches)} matches, {metrics.event_count} events")
    print(f"Before player/team IDs: {result.baseline_lineup}")
    print(
        f"Replace slot {result.replacement_slot}: {result.replaced_id} with {result.candidate_id}"
    )
    print(f"After player/team IDs: {result.updated_lineup}")
    print(
        f"Fixed comparison IDs: {tuple(row.player_team_id for row in result.comparison_cohort)}"
    )
    print(f"Fixed feature ranges: {result.feature_ranges}; weights: {result.weights}")
    for profile in result.comparison_cohort:
        print(
            f"Sample {profile.player_team_id}: minutes={profile.player.rated_minutes:.2f}, "
            f"rated/appearances={profile.rated_matches}/{profile.recorded_appearances}, "
            f"coverage={profile.appearance_coverage:.2%}, "
            f"unrecorded_event_matches={profile.unrecorded_event_matches}"
        )
    for feature in result.features:
        print(
            f"{feature.metric}: raw_before={feature.before_values} raw_after={feature.after_values}; "
            f"mean {feature.before_mean:.4f} -> {feature.after_mean:.4f} "
            f"(delta {feature.mean_change:+.4f}); "
            f"normalized coverage {feature.before_coverage:.4f} -> {feature.after_coverage:.4f} "
            f"(delta {feature.coverage_change:+.4f}); weighted change={feature.weighted_change:+.4f} points"
        )
    print(
        f"Weighted coverage change: {result.weighted_coverage_change:+.4f} index points (not a team-fit rating)"
    )
    print(
        f"Unknown-player events: {len(metrics.unknown_player_event_ids)}; "
        f"events without recorded appearances: {len(metrics.non_appearance_event_ids)}"
    )
    for warning in result.warnings:
        print(f"warning: {warning}")
    for limitation in result.limitations:
        print(f"limitation: {limitation}")
    print(
        "Original match-level timing/metric warnings remain in each comparison profile's player.matches."
    )
    print(
        f"Runtime seconds: loading/metrics={calculated - started:.6f} "
        f"comparison={compared - calculated:.6f} total={compared - started:.6f}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
