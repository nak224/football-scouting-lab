"""Compose existing style and role results into an explained replacement ranking."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass

from .metrics import PlayerSeasonMetrics
from .roles import (
    EligibilityThresholds,
    PositionReview,
    RoleFit,
    RoleRanking,
    score_role,
)
from .similarity import PlayerSimilarity, SimilarityResult, compare_styles


@dataclass(frozen=True)
class ReplacementCandidate:
    style: PlayerSimilarity
    role: RoleFit
    style_contribution: float | None
    role_contribution: float | None
    combined_score: float | None
    reasons: tuple[str, ...]

    @property
    def candidate_id(self) -> tuple[int, int]:
        return self.style.candidate_id


@dataclass(frozen=True)
class RecruitmentRanking:
    style_priority: float
    limit: int | None
    style: SimilarityResult
    role: RoleRanking
    candidates: tuple[ReplacementCandidate, ...]  # All rows, including exclusions.
    shortlist: tuple[ReplacementCandidate, ...]
    warnings: tuple[str, ...]

    @property
    def reference_id(self) -> tuple[int, int]:
        player = self.style.reference.player
        return player.player_id, player.team_id


def rank_replacements(
    players: Iterable[PlayerSeasonMetrics],
    reviews: Mapping[tuple[int, int], PositionReview],
    reference: tuple[int, int],
    role: str,
    *,
    style_priority: float = 0.5,
    style_weights: Mapping[str, float] | None = None,
    role_weights: Mapping[str, float] | None = None,
    thresholds: EligibilityThresholds = EligibilityThresholds(),
    limit: int | None = None,
) -> RecruitmentRanking:
    """Blend two available scores; never refit their normalization distributions.

    Both scores are required even at priorities 0 and 1. The reference must pass
    compare_styles validation; its own selected role score need not be available.
    Retain source objects, sample context and reasons unchanged. See docs/recruitment.md.
    """
    if type(style_priority) not in (int, float) or not 0 <= style_priority <= 1:
        raise ValueError("style_priority must be a finite number in [0, 1]")
    if limit is not None and (type(limit) is not int or limit < 0):
        raise ValueError("shortlist limit must be a nonnegative integer or None")
    players = tuple(
        players
    )  # Both algorithms must see the same input, including generators.
    style_result = compare_styles(
        players, reviews, reference, weights=style_weights, thresholds=thresholds
    )
    role_result = score_role(
        players, reviews, role, weights=role_weights, thresholds=thresholds
    )
    role_rows = {
        (row.eligibility.player.player_id, row.eligibility.player.team_id): row
        for row in role_result.candidates
    }
    candidates = []
    for style_row in style_result.candidates:
        role_row = role_rows[style_row.candidate_id]
        reasons = []
        if style_row.candidate_id[0] == reference[0]:
            reasons.append("same underlying player as reference")
        for name, row in (("style", style_row), ("role", role_row)):
            if row.score is None:
                reasons.append(f"{name} score unavailable")
            reasons.extend(f"{name}: {reason}" for reason in row.reasons)
        style_points = (
            style_priority * style_row.score if style_row.score is not None else None
        )
        role_points = (
            (1 - style_priority) * role_row.score
            if role_row.score is not None
            else None
        )
        candidates.append(
            ReplacementCandidate(
                style_row,
                role_row,
                style_points,
                role_points,
                style_points + role_points if not reasons else None,
                tuple(reasons),
            )
        )
    candidates.sort(
        key=lambda row: (
            row.combined_score is None,
            -(row.combined_score or 0),
            *row.candidate_id,
        )
    )
    available = tuple(row for row in candidates if row.combined_score is not None)
    warnings = []
    if not available:
        warnings.append("no complete replacement candidates after self-exclusion")
    if limit is not None and len(available) < limit:
        warnings.append(
            f"requested {limit} rows; only {len(available)} complete replacements available"
        )
    return RecruitmentRanking(
        style_priority,
        limit,
        style_result,
        role_result,
        tuple(candidates),
        available if limit is None else available[:limit],
        tuple(warnings),
    )
