"""Fixed-cohort statistical coverage for a hypothetical 4-3-3 midfield trio."""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .metrics import PlayerSeasonMetrics

PlayerTeamId = tuple[int, int]
PROFILE_METRICS = (
    "pass_attempts_per90",
    "pass_completion_pct",
    "interceptions_per90",
    "successful_defensive_duels_per90",
)
LIMITATIONS = (
    "User-selected hypothetical 4-3-3 midfield slots are not observed tactical positions; "
    "players from different historical clubs are not assumed to have played together.",
    "Coverage is the strongest individual feature representation, not trio production, "
    "chemistry, synergy, tactical suitability or a match-outcome prediction.",
    "Different samples, clubs, possession and opponents limit comparison; estimated "
    "minutes and appearance coverage do not certify complete event data.",
    "The caller selects and reviews the fixed comparison cohort; this function "
    "does not infer positions, select eligible midfielders or blend recruitment scores.",
)


@dataclass(frozen=True)
class PlayerProfile:
    player: PlayerSeasonMetrics  # Retain original player/team IDs and match warnings.
    measurements: dict[str, float]
    recorded_appearances: int
    rated_matches: int
    appearance_coverage: float
    unrecorded_event_matches: int

    @property
    def player_team_id(self) -> PlayerTeamId:
        return self.player.player_id, self.player.team_id


@dataclass(frozen=True)
class FeatureChange:
    metric: str
    weight: float
    before_values: tuple[float, ...]  # Ordered by the original/updated slots.
    after_values: tuple[float, ...]
    before_mean: float  # Equal-player mean, NOT pooled team completion or event rate.
    after_mean: float
    mean_change: float
    before_coverage: float  # Maximum normalized individual value in this trio.
    after_coverage: float
    coverage_change: float
    weighted_change: float  # 100 * weight * coverage_change, in index points.


@dataclass(frozen=True)
class MidfieldComparison:
    baseline_lineup: tuple[PlayerTeamId, ...]
    replacement_slot: int  # Zero-based index; no left/right/holding-role inference.
    replaced_id: PlayerTeamId
    candidate_id: PlayerTeamId
    updated_lineup: tuple[PlayerTeamId, ...]
    before: tuple[PlayerProfile, ...]
    after: tuple[PlayerProfile, ...]
    comparison_cohort: tuple[PlayerProfile, ...]  # Sorted by original player/team IDs.
    feature_ranges: dict[str, tuple[float, float]]
    weights: dict[str, float]
    features: tuple[FeatureChange, ...]
    weighted_coverage_change: float  # Signed summary, not a team-fit rating.
    warnings: tuple[str, ...]
    limitations: tuple[str, ...] = LIMITATIONS


def _finite(value: object) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _key(value: PlayerTeamId) -> PlayerTeamId:
    if (
        not isinstance(value, tuple)
        or len(value) != 2
        or any(type(part) is not int or part <= 0 for part in value)
    ):
        raise ValueError("player/team IDs must be (positive player_id, team_id) tuples")
    return value


def normalize_profile_weights(
    weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Equal defaults; custom weights replace them. All four features stay visible."""
    supplied = dict.fromkeys(PROFILE_METRICS, 1.0) if weights is None else dict(weights)
    if supplied.keys() - set(PROFILE_METRICS):
        raise ValueError("unknown profile metric in weights")
    if not supplied or any(
        not _finite(value) or value < 0 for value in supplied.values()
    ):
        raise ValueError("profile weights must be finite, nonnegative numbers")
    scale = max(supplied.values())
    if scale == 0:
        raise ValueError("at least one profile weight must be positive")
    total = math.fsum(value / scale for value in supplied.values())
    return {
        metric: (supplied.get(metric, 0) / scale) / total for metric in PROFILE_METRICS
    }


def prepare_player_profile(player: PlayerSeasonMetrics) -> PlayerProfile:
    """Validate one complete rated sample without choosing a cohort or scales."""
    key = _key((player.player_id, player.team_id))
    if (
        player.rated is None
        or not _finite(player.rated_minutes)
        or player.rated_minutes <= 0
    ):
        raise ValueError(
            f"comparison cohort {key}: positive rated minutes and counts required"
        )
    rates = player.per90
    measurements = {
        metric: (
            player.rated.pass_completion_pct
            if metric == "pass_completion_pct"
            else rates[metric.removesuffix("_per90")]
        )
        for metric in PROFILE_METRICS
    }
    missing = [
        metric
        for metric, value in measurements.items()
        if not _finite(value)
        or value < 0
        or (metric == "pass_completion_pct" and value > 100)
    ]
    if missing:
        raise ValueError(
            f"comparison cohort {key}: unavailable/invalid metrics: {', '.join(missing)}"
        )
    appearances = [row for row in player.matches if row.appearance_recorded]
    rated = sum(row.rate_eligible for row in appearances)
    if not appearances or not rated:
        raise ValueError(
            f"comparison cohort {key}: rated recorded appearances required"
        )
    return PlayerProfile(
        player,
        measurements,
        len(appearances),
        rated,
        rated / len(appearances),
        sum(not row.appearance_recorded for row in player.matches),
    )


def compare_midfield(
    comparison_cohort: Iterable[PlayerSeasonMetrics],
    baseline_lineup: Iterable[PlayerTeamId],
    replacement_slot: int,
    candidate_id: PlayerTeamId,
    *,
    weights: Mapping[str, float] | None = None,
) -> MidfieldComparison:
    """Compare marginal feature coverage; caller supplies ONE fixed, complete cohort.

    All lineup/candidate rows must belong to that cohort. All four measurements
    are required even at zero weight. No automatic exclusions, scale refitting,
    current-team inference, minute imputation or source-object mutation.
    See docs/team-fit.md for formulas, constant features and interpretation limits.
    """
    weights = normalize_profile_weights(weights)
    baseline = tuple(_key(key) for key in baseline_lineup)
    if len(baseline) != 3 or len({key[0] for key in baseline}) != 3:
        raise ValueError(
            "baseline requires three distinct underlying players across historical team rows"
        )
    if type(replacement_slot) is not int or not 0 <= replacement_slot < 3:
        raise ValueError("replacement slot must be an integer index 0, 1 or 2")
    candidate_id = _key(candidate_id)
    if candidate_id[0] in {key[0] for key in baseline}:
        raise ValueError(
            "candidate already present in baseline lineup, including historical team rows"
        )
    players = tuple(comparison_cohort)
    keys = [_key((row.player_id, row.team_id)) for row in players]
    if len(set(keys)) != len(keys):
        raise ValueError("duplicate player/team rows in comparison cohort")
    required = {*baseline, candidate_id}
    if missing := required - set(keys):
        raise ValueError(
            f"lineup/candidate absent from fixed comparison cohort: {sorted(missing)}"
        )
    profiles = tuple(
        prepare_player_profile(row)
        for row in sorted(players, key=lambda p: (p.player_id, p.team_id))
    )
    indexed = {row.player_team_id: row for row in profiles}
    updated = (
        baseline[:replacement_slot] + (candidate_id,) + baseline[replacement_slot + 1 :]
    )
    before = tuple(indexed[key] for key in baseline)
    after = tuple(indexed[key] for key in updated)
    warnings = []
    unique_players = len({key[0] for key in keys})
    if unique_players == 4:
        warnings.append(
            "tiny comparison cohort: only four distinct players; coverage is demonstration-only"
        )
    if unique_players < len(keys):
        warnings.append(
            "comparison cohort contains historical team rows for the same player; samples stay separate"
        )
    for profile in profiles:
        if profile.appearance_coverage < 1:
            warnings.append(
                f"{profile.player_team_id}: incomplete appearance coverage ({profile.rated_matches}/{profile.recorded_appearances})"
            )
        if profile.unrecorded_event_matches:
            warnings.append(
                f"{profile.player_team_id}: events without recorded appearances; inspect source match warnings"
            )
    features, ranges = [], {}
    for metric in PROFILE_METRICS:
        values = [row.measurements[metric] for row in profiles]
        low, high = min(values), max(values)
        ranges[metric] = (low, high)
        if low == high:
            warnings.append(
                f"constant feature {metric}: neutral normalization 0.5; no distinguishable coverage change"
            )
        before_values = tuple(row.measurements[metric] for row in before)
        after_values = tuple(row.measurements[metric] for row in after)
        before_mean = math.fsum(value / 3 for value in before_values)
        after_mean = math.fsum(value / 3 for value in after_values)
        before_coverage = (
            0.5 if low == high else (max(before_values) - low) / (high - low)
        )
        after_coverage = (
            0.5 if low == high else (max(after_values) - low) / (high - low)
        )
        change = after_coverage - before_coverage
        features.append(
            FeatureChange(
                metric,
                weights[metric],
                before_values,
                after_values,
                before_mean,
                after_mean,
                after_mean - before_mean,
                before_coverage,
                after_coverage,
                change,
                100 * weights[metric] * change,
            )
        )
    return MidfieldComparison(
        baseline,
        replacement_slot,
        baseline[replacement_slot],
        candidate_id,
        updated,
        before,
        after,
        profiles,
        ranges,
        weights,
        tuple(features),
        math.fsum(row.weighted_change for row in features),
        tuple(warnings),
    )
