"""Explicit cohort eligibility and weighted, cohort-relative tactical role fits."""

import math
from bisect import bisect_left, bisect_right
from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .metrics import PlayerSeasonMetrics

ROLE_TEMPLATES = {
    "deep_lying_playmaker": {
        "pass_attempts_per90": 0.4,
        "pass_completion_pct": 0.3,
        "accurate_passes_per90": 0.3,
    },
    "ball_winning_midfielder": {
        "interceptions_per90": 0.45,
        "successful_defensive_duels_per90": 0.4,
        "pass_attempts_per90": 0.15,
    },
}


def _finite(value: object) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


@dataclass(frozen=True)
class PositionReview:
    """A scoped inclusion decision, not a position inferred from source metrics."""

    status: str  # included, excluded, or unverified
    evidence: str = ""
    note: str = ""

    def __post_init__(self) -> None:
        if self.status not in ("included", "excluded", "unverified"):
            raise ValueError(
                "position review status must be included/excluded/unverified"
            )
        if not isinstance(self.evidence, str) or not isinstance(self.note, str):
            raise ValueError("review evidence and note must be strings")
        if self.status != "unverified" and (
            not self.evidence.strip() or not self.note.strip()
        ):
            raise ValueError("a position decision requires evidence and a review note")


@dataclass(frozen=True)
class EligibilityThresholds:
    min_rated_minutes: float = 600
    min_appearance_coverage: float = 0.6

    def __post_init__(self) -> None:
        if not _finite(self.min_rated_minutes) or self.min_rated_minutes < 0:
            raise ValueError("minimum rated minutes must be finite and nonnegative")
        if not _finite(self.min_appearance_coverage) or not (
            0 <= self.min_appearance_coverage <= 1
        ):
            raise ValueError("minimum appearance coverage must be between 0 and 1")


@dataclass(frozen=True)
class CandidateEligibility:
    player: PlayerSeasonMetrics
    review: PositionReview
    recorded_appearances: int
    rated_matches: int
    appearance_coverage: float | None
    unrecorded_event_matches: int
    reasons: tuple[str, ...]

    @property
    def eligible(self) -> bool:
        return not self.reasons


def assess_eligibility(
    players: Iterable[PlayerSeasonMetrics],
    reviews: Mapping[tuple[int, int], PositionReview],
    thresholds: EligibilityThresholds = EligibilityThresholds(),
) -> tuple[CandidateEligibility, ...]:
    """Reviews are keyed by (player_id, historical_team_id); no transfer inference."""
    players = sorted(players, key=lambda p: (p.player_id, p.team_id))
    keys = {(p.player_id, p.team_id) for p in players}
    if len(keys) != len(players):
        raise ValueError("duplicate player/team metric rows")
    if reviews.keys() - keys:
        raise ValueError("position review references a player/team absent from metrics")
    results = []
    for player in players:
        review = reviews.get(
            (player.player_id, player.team_id), PositionReview("unverified")
        )
        appearances = [m for m in player.matches if m.appearance_recorded]
        rated = sum(m.rate_eligible for m in appearances)
        coverage = rated / len(appearances) if appearances else None
        reasons = []
        if review.status != "included":
            reasons.append(f"position review: {review.status}")
        if not _finite(player.rated_minutes) or player.rated_minutes <= 0:
            reasons.append("positive rated minutes unavailable")
        elif player.rated_minutes < thresholds.min_rated_minutes:
            reasons.append("below minimum rated minutes")
        if player.rated is None:
            reasons.append("rated event counts unavailable")
        if coverage is None:
            reasons.append("no recorded appearances")
        elif coverage < thresholds.min_appearance_coverage:
            reasons.append("below minimum appearance coverage")
        results.append(
            CandidateEligibility(
                player,
                review,
                len(appearances),
                rated,
                coverage,
                sum(not m.appearance_recorded for m in player.matches),
                tuple(reasons),
            )
        )
    return tuple(results)


@dataclass(frozen=True)
class MetricContribution:
    metric: str
    measurement: float
    percentile: float
    weight: float
    points: float


@dataclass(frozen=True)
class RoleFit:
    eligibility: CandidateEligibility
    measurements: dict[str, float | None]
    score: float | None
    contributions: tuple[MetricContribution, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class RoleRanking:
    role: str
    thresholds: EligibilityThresholds
    weights: dict[str, float]
    reference_ids: tuple[tuple[int, int], ...]
    candidates: tuple[RoleFit, ...]  # Scored first, exclusions retained.


def normalize_weights(
    role: str, weights: Mapping[str, float] | None = None
) -> dict[str, float]:
    """Custom mappings replace the template; omitted/zero weights disable a metric."""
    if role not in ROLE_TEMPLATES:
        raise ValueError(f"unknown tactical role: {role!r}")
    supplied = dict(ROLE_TEMPLATES[role] if weights is None else weights)
    if supplied.keys() - ROLE_TEMPLATES[role].keys():
        raise ValueError("weights contain metrics outside the selected role template")
    if not supplied or any(not _finite(w) or w < 0 for w in supplied.values()):
        raise ValueError("weights must be finite, nonnegative numbers")
    scale = max(supplied.values())
    if scale == 0:
        raise ValueError("at least one metric weight must be positive")
    # Scaling before summation also supports very large finite custom weights.
    total = math.fsum(w / scale for w in supplied.values())
    return {name: (supplied[name] / scale) / total for name in sorted(supplied)}


def _measurements(player: PlayerSeasonMetrics) -> dict[str, float | None]:
    return {
        **{
            f"{name}_per90": value if player.rated is not None else None
            for name, value in player.per90.items()
        },
        "pass_completion_pct": (
            player.rated.pass_completion_pct if player.rated is not None else None
        ),
    }


def score_role(
    players: Iterable[PlayerSeasonMetrics],
    reviews: Mapping[tuple[int, int], PositionReview],
    role: str,
    *,
    weights: Mapping[str, float] | None = None,
    thresholds: EligibilityThresholds = EligibilityThresholds(),
) -> RoleRanking:
    """Score complete eligible rows using weighted empirical midranks (0–100).

    Missing required metrics exclude a row from both scoring and normalization.
    See docs/roles.md for small-cohort conventions and interpretation limits.
    """
    normalized = normalize_weights(role, weights)
    required = [name for name, weight in normalized.items() if weight > 0]
    prepared = []
    for candidate in assess_eligibility(players, reviews, thresholds):
        values = _measurements(candidate.player)
        missing = tuple(
            f"unavailable required metric: {name}"
            for name in required
            if not _finite(values[name]) or values[name] < 0
        )
        prepared.append((candidate, values, candidate.reasons + missing))
    pool = [(c, v) for c, v, reasons in prepared if not reasons]
    distributions = {name: sorted(v[name] for _, v in pool) for name in required}
    results = []
    for candidate, values, reasons in prepared:
        contributions = []
        if not reasons:
            for name in required:
                distribution = distributions[name]
                value = values[name]
                lower = bisect_left(distribution, value)
                equal = bisect_right(distribution, value) - lower
                percentile = (
                    50.0
                    if len(pool) == 1
                    else 100 * (lower + (equal - 1) / 2) / (len(pool) - 1)
                )
                contributions.append(
                    MetricContribution(
                        name,
                        value,
                        percentile,
                        normalized[name],
                        percentile * normalized[name],
                    )
                )
        results.append(
            RoleFit(
                candidate,
                values,
                math.fsum(c.points for c in contributions) if not reasons else None,
                tuple(contributions),
                reasons,
            )
        )
    results.sort(
        key=lambda r: (
            r.score is None,
            -(r.score or 0),
            r.eligibility.player.player_id,
            r.eligibility.player.team_id,
        )
    )
    return RoleRanking(
        role,
        thresholds,
        normalized,
        tuple((c.player.player_id, c.player.team_id) for c, _ in pool),
        tuple(results),
    )
