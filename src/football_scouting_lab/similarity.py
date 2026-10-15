"""Explainable playing-style distances, independent of tactical-role scoring."""

import math
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .metrics import PlayerSeasonMetrics
from .roles import (
    CandidateEligibility,
    EligibilityThresholds,
    PositionReview,
    assess_eligibility,
)

STYLE_METRICS = (
    "pass_attempts_per90",
    "pass_completion_pct",
    "interceptions_per90",
    "successful_defensive_duels_per90",
)


def _finite(value: object) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def normalize_style_weights(
    weights: Mapping[str, float] | None = None,
) -> dict[str, float]:
    """Custom mappings replace equal defaults; omitted/zero metrics are disabled."""
    supplied = dict.fromkeys(STYLE_METRICS, 1.0) if weights is None else dict(weights)
    if supplied.keys() - set(STYLE_METRICS):
        raise ValueError("unknown style metric in weights")
    if not supplied or any(not _finite(w) or w < 0 for w in supplied.values()):
        raise ValueError("style weights must be finite, nonnegative numbers")
    scale = max(supplied.values())
    if scale == 0:
        raise ValueError("at least one style weight must be positive")
    total = math.fsum(w / scale for w in supplied.values())
    return {name: (supplied[name] / scale) / total for name in sorted(supplied)}


@dataclass(frozen=True)
class FeatureDifference:
    metric: str
    reference_value: float
    candidate_value: float
    raw_difference: float  # Candidate minus reference; retains direction.
    reference_normalized: float
    candidate_normalized: float
    normalized_difference: float  # Absolute difference on [0, 1].
    weight: float
    contribution: float  # Weighted contribution to distance, not role fit.


@dataclass(frozen=True)
class PlayerSimilarity:
    reference_id: tuple[int, int]
    candidate: CandidateEligibility
    measurements: dict[str, float | None]
    distance: float | None
    score: float | None
    differences: tuple[FeatureDifference, ...]
    reasons: tuple[str, ...]

    @property
    def candidate_id(self) -> tuple[int, int]:
        return self.candidate.player.player_id, self.candidate.player.team_id


@dataclass(frozen=True)
class SimilarityResult:
    reference: CandidateEligibility
    reference_values: dict[str, float | None]
    thresholds: EligibilityThresholds
    weights: dict[str, float]
    normalization_ids: tuple[tuple[int, int], ...]
    feature_ranges: dict[str, tuple[float, float]]
    warnings: tuple[str, ...]
    candidates: tuple[PlayerSimilarity, ...]  # Includes self and explicit exclusions.


def _measurements(player: PlayerSeasonMetrics) -> dict[str, float | None]:
    rates = player.per90
    return {
        name: (
            None
            if player.rated is None
            else player.rated.pass_completion_pct
            if name == "pass_completion_pct"
            else rates[name.removesuffix("_per90")]
        )
        for name in STYLE_METRICS
    }


def compare_styles(
    players: Iterable[PlayerSeasonMetrics],
    reviews: Mapping[tuple[int, int], PositionReview],
    reference: tuple[int, int],
    *,
    weights: Mapping[str, float] | None = None,
    thresholds: EligibilityThresholds = EligibilityThresholds(),
) -> SimilarityResult:
    """Compare with weighted min-max/L1 distance; similarity = 100 * (1-distance).

    Only complete eligible rows define the shared scale, including the reference.
    Missing/ineligible references raise ValueError; other exclusions remain visible.
    No role scores or role weights are read. See docs/similarity.md.
    """
    normalized = normalize_style_weights(weights)
    if (
        not isinstance(reference, tuple)
        or len(reference) != 2
        or any(type(value) is not int or value <= 0 for value in reference)
    ):
        raise ValueError("reference must be a (positive player_id, team_id) tuple")
    required = [name for name, weight in normalized.items() if weight > 0]
    prepared = []
    for candidate in assess_eligibility(players, reviews, thresholds):
        values = _measurements(candidate.player)
        missing = tuple(
            f"unavailable or invalid style metric: {name}"
            for name in required
            if not _finite(values[name])
            or values[name] < 0
            or (name == "pass_completion_pct" and values[name] > 100)
        )
        prepared.append((candidate, values, candidate.reasons + missing))
    target = next(
        (
            row
            for row in prepared
            if (row[0].player.player_id, row[0].player.team_id) == reference
        ),
        None,
    )
    if target is None:
        raise ValueError(f"reference {reference} is absent from player/team metrics")
    reference_candidate, reference_values, reference_reasons = target
    if reference_reasons:
        raise ValueError(
            f"reference {reference} cannot be compared: {'; '.join(reference_reasons)}"
        )
    pool = [(c, v) for c, v, reasons in prepared if not reasons]
    ranges = {
        name: (min(v[name] for _, v in pool), max(v[name] for _, v in pool))
        for name in required
    }
    warnings = []
    if len(pool) <= 2:
        warnings.append(
            f"tiny normalization cohort ({len(pool)} rows); distances are unstable"
        )
    constants = [name for name, (low, high) in ranges.items() if low == high]
    if constants:
        warnings.append(
            f"constant features contribute zero distance: {', '.join(constants)}"
        )
    if len(constants) == len(required):
        warnings.append(
            "no selected feature distinguishes this cohort; 100 is uninformative"
        )
    results = []
    for candidate, values, reasons in prepared:
        differences = []
        if not reasons:
            for name in required:
                low, high = ranges[name]
                ref = (
                    0.5
                    if high == low
                    else (reference_values[name] - low) / (high - low)
                )
                other = 0.5 if high == low else (values[name] - low) / (high - low)
                difference = abs(other - ref)
                differences.append(
                    FeatureDifference(
                        name,
                        reference_values[name],
                        values[name],
                        values[name] - reference_values[name],
                        ref,
                        other,
                        difference,
                        normalized[name],
                        normalized[name] * difference,
                    )
                )
        # Bound floating-point summation drift, without changing measurements.
        distance = (
            min(1.0, max(0.0, math.fsum(d.contribution for d in differences)))
            if not reasons
            else None
        )
        results.append(
            PlayerSimilarity(
                reference,
                candidate,
                values,
                distance,
                100 * (1 - distance) if distance is not None else None,
                tuple(differences),
                reasons,
            )
        )
    results.sort(key=lambda r: (r.score is None, -(r.score or 0), *r.candidate_id))
    if not any(
        r.score is not None and r.candidate_id[0] != reference[0] for r in results
    ):
        warnings.append(
            "no eligible replacement candidates after excluding the reference player ID"
        )
    return SimilarityResult(
        reference_candidate,
        reference_values,
        thresholds,
        normalized,
        tuple((c.player.player_id, c.player.team_id) for c, _ in pool),
        ranges,
        tuple(warnings),
        tuple(results),
    )


def replacement_shortlist(
    result: SimilarityResult, *, limit: int | None = None
) -> tuple[PlayerSimilarity, ...]:
    """Rank eligible historical team rows; never recommend the reference player."""
    if limit is not None and (type(limit) is not int or limit < 0):
        raise ValueError("shortlist limit must be a nonnegative integer or None")
    rows = tuple(
        row
        for row in result.candidates
        if row.score is not None
        and row.candidate_id[0] != result.reference.player.player_id
    )
    return rows if limit is None else rows[:limit]
