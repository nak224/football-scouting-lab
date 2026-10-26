"""Discovery and per-feature comparisons of existing rated player/team statistics.

No position inference, recruitment eligibility, role scores or new football metrics.
"""

import math
from dataclasses import dataclass

from .metrics import PlayerSeasonMetrics
from .similarity import STYLE_METRICS
from .ui_data import POSITION_GROUPS, ScoutingData

LEAGUE = "Bundesliga 2017/18"
SEASON = "2017/18"
MIN_COMPARISON_MINUTES = 600
FEATURES = STYLE_METRICS
LABELS = {
    "pass_attempts_per90": "Pass attempts /90",
    "pass_completion_pct": "Pass completion %",
    "interceptions_per90": "Interceptions /90",
    "successful_defensive_duels_per90": "Successful defensive duels /90",
}


def _finite(value) -> bool:
    return type(value) in (int, float) and math.isfinite(value)


def position(data: ScoutingData, player_id: int) -> str:
    value = data.player_positions.get(player_id)
    return value if value in POSITION_GROUPS else "Unknown"


def measurements(player: PlayerSeasonMetrics) -> dict[str, float | None]:
    """Keep missing rated samples unavailable, including counts with unknown time."""
    usable = (
        player.rated is not None
        and _finite(player.rated_minutes)
        and player.rated_minutes > 0
    )
    values = {}
    for metric in FEATURES:
        value = None
        if usable:
            value = (
                player.rated.pass_completion_pct
                if metric == "pass_completion_pct"
                else player.per90[metric.removesuffix("_per90")]
            )
        valid = _finite(value) and value >= 0
        if metric == "pass_completion_pct":
            valid = valid and value <= 100
        values[metric] = value if valid else None
    return values


def discovery_rows(
    data: ScoutingData,
    *,
    query: str = "",
    league: str = LEAGUE,
    team_id: int | None = None,
    player_position: str | None = None,
) -> list[dict]:
    """Compact display rows; IDs stay available internally for native row selection."""
    rows = []
    for player in data.metrics.players:
        name = data.player_names.get(player.player_id, f"Player {player.player_id}")
        group = position(data, player.player_id)
        if (
            league != LEAGUE
            or query.strip().casefold() not in name.casefold()
            or (team_id is not None and player.team_id != team_id)
            or (player_position is not None and group != player_position)
        ):
            continue
        rows.append(
            {
                "Name": name,
                "Historical team": data.team_names.get(
                    player.team_id, f"Team {player.team_id}"
                ),
                "Position": group,
                "Rated minutes": player.rated_minutes
                if _finite(player.rated_minutes) and player.rated_minutes > 0
                else None,
                **{LABELS[key]: value for key, value in measurements(player).items()},
                "Player ID": player.player_id,
                "Team ID": player.team_id,
            }
        )
    return sorted(
        rows,
        key=lambda row: (
            row["Rated minutes"] is None,
            -(row["Rated minutes"] or 0),
            row["Player ID"],
            row["Team ID"],
        ),
    )


def selected_player(rows: list[dict], indices: list[int]) -> tuple[int, int] | None:
    """Streamlit supplies original input row indices even after client-side sorting."""
    if (
        len(indices) != 1
        or type(indices[0]) is not int
        or not 0 <= indices[0] < len(rows)
    ):
        return None
    row = rows[indices[0]]
    return row["Player ID"], row["Team ID"]


@dataclass(frozen=True)
class FeatureComparison:
    metric: str
    value: float | None
    percentile: float | None
    peer_count: int


@dataclass(frozen=True)
class PlayerComparison:
    player_team_id: tuple[int, int]
    mode: str
    peer_ids: tuple[tuple[int, int], ...]
    features: tuple[FeatureComparison, ...]


def compare_player(
    data: ScoutingData,
    player_team_id: tuple[int, int],
    *,
    mode: str = "Same position",
    min_minutes: float = MIN_COMPARISON_MINUTES,
) -> PlayerComparison:
    """Midrank CDF: 100 * (strictly lower + 0.5 * equal) / feature peer count.

    Transfers remain separate rows. The reference is included if it qualifies.
    At least two finite peers are required per feature; ties/constant groups are
    neutral at 50 when the target equals all peers. Low-minute targets can still
    be compared against the qualified population; their own row is not included.
    """
    players, peer_ids, peers = _population(data, player_team_id, mode, min_minutes)
    return _profile(players[player_team_id], peer_ids, peers, mode)


def _population(data, player_team_id, mode, min_minutes=MIN_COMPARISON_MINUTES):
    """One fixed source/position population, independent of Player B or search filters."""
    if mode not in ("Same position", "All players"):
        raise ValueError("comparison mode must be Same position or All players")
    if not _finite(min_minutes) or min_minutes <= 0:
        raise ValueError("comparison minimum minutes must be finite and positive")
    players = {(row.player_id, row.team_id): row for row in data.metrics.players}
    if len(players) != len(data.metrics.players):
        raise ValueError("duplicate player/team metric rows")
    if player_team_id not in players:
        raise ValueError("selected player/team is absent from this source")
    target_position = position(data, player_team_id[0])
    peer_ids = tuple(
        sorted(
            key
            for key, player in players.items()
            if _finite(player.rated_minutes)
            and player.rated_minutes >= min_minutes
            and player.rated is not None
            and any(
                match.appearance_recorded and match.rate_eligible
                for match in player.matches
            )
            and (
                mode == "All players"
                or (
                    target_position != "Unknown"
                    and position(data, key[0]) == target_position
                )
            )
        )
    )
    return players, peer_ids, [measurements(players[key]) for key in peer_ids]


def _profile(player, peer_ids, peers, mode):
    target = measurements(player)
    features = []
    for metric, value in target.items():
        sample = [peer[metric] for peer in peers if peer[metric] is not None]
        percentile = None
        if value is not None and len(sample) >= 2:
            percentile = (
                100
                * (
                    sum(x < value for x in sample)
                    + 0.5 * sum(x == value for x in sample)
                )
                / len(sample)
            )
        features.append(FeatureComparison(metric, value, percentile, len(sample)))
    return PlayerComparison(
        (player.player_id, player.team_id), mode, peer_ids, tuple(features)
    )


def radar_features(result: PlayerComparison) -> tuple[FeatureComparison, ...]:
    """A polygon needs three comparable measurements; never pad with invented zeroes."""
    features = tuple(row for row in result.features if row.percentile is not None)
    return features if len(features) >= 3 else ()


@dataclass(frozen=True)
class ProfilePair:
    reference: PlayerComparison
    candidate: PlayerComparison
    common_metrics: tuple[str, ...]
    similarity: float | None
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SimilarProfiles:
    reference: PlayerComparison
    feature_basis: tuple[str, ...]
    matches: tuple[ProfilePair, ...]
    exclusions: tuple[tuple[tuple[int, int], tuple[str, ...]], ...]
    warnings: tuple[str, ...]


def _sample_reasons(player):
    reasons = []
    if (
        not _finite(player.rated_minutes)
        or player.rated_minutes < MIN_COMPARISON_MINUTES
    ):
        reasons.append("fewer than 600 valid rated minutes")
    if player.rated is None:
        reasons.append("rated measurements unavailable")
    if not any(
        match.appearance_recorded and match.rate_eligible for match in player.matches
    ):
        reasons.append("no rated recorded appearance")
    return reasons


def _basis(reference):
    return tuple(row.metric for row in reference.features if row.percentile is not None)


def _pair(reference, candidate, reference_issues, candidate_issues):
    basis = _basis(reference)
    available = {
        row.metric: row.percentile
        for row in candidate.features
        if row.percentile is not None
    }
    common = tuple(metric for metric in basis if metric in available)
    reasons = [*reference_issues, *candidate_issues]
    missing = [LABELS[metric] for metric in basis if metric not in available]
    if missing:
        reasons.append("missing reference features: " + ", ".join(missing))
    score = None
    if not reasons:
        distance = sum(
            abs(row.percentile - available[row.metric])
            for row in reference.features
            if row.metric in basis
        ) / len(basis)
        score = 100 - distance
    return ProfilePair(reference, candidate, common, score, tuple(reasons))


def _reference_issues(player, reference):
    issues = [f"Player A: {reason}" for reason in _sample_reasons(player)]
    if len(_basis(reference)) < 3:
        issues.append(
            "Player A needs at least three comparable features with two peers each"
        )
    return issues


def compare_pair(
    data, reference_id, candidate_id, *, mode="Same position"
) -> ProfilePair:
    """Both percentiles use A's fixed population. Manual pairs may expose missing scores.

    Similarity = 100 - mean absolute percentile difference, using every available
    reference feature (minimum three). It is descriptive, not a probability/fit.
    Incomplete or low-minute players retain raw comparisons without a score.
    """
    players, peer_ids, peers = _population(data, reference_id, mode)
    if candidate_id not in players:
        raise ValueError("Player B is absent from this source")
    if candidate_id[0] == reference_id[0]:
        raise ValueError("Choose a different underlying player for Player B")
    if mode == "Same position" and (
        position(data, reference_id[0]) == "Unknown"
        or position(data, candidate_id[0]) != position(data, reference_id[0])
    ):
        raise ValueError("Choose All players to compare different or unknown positions")
    reference = _profile(players[reference_id], peer_ids, peers, mode)
    candidate = _profile(players[candidate_id], peer_ids, peers, mode)
    return _pair(
        reference,
        candidate,
        _reference_issues(players[reference_id], reference),
        _sample_reasons(players[candidate_id]),
    )


def similar_profiles(data, reference_id, *, mode="Same position") -> SimilarProfiles:
    """Top five source-wide matches on one frozen reference feature basis.

    Recruitment reviews and search filters never define the population or ranks.
    Missing reference features are omitted uniformly for ALL candidates. Candidates
    must supply the complete remaining basis, rather than gain from missing values.
    """
    players, peer_ids, peers = _population(data, reference_id, mode)
    reference = _profile(players[reference_id], peer_ids, peers, mode)
    issues = _reference_issues(players[reference_id], reference)
    matches, exclusions = [], []
    for key, player in sorted(players.items()):
        if key[0] == reference_id[0]:
            continue
        reasons = _sample_reasons(player)
        if mode == "Same position" and (
            position(data, reference_id[0]) == "Unknown"
            or position(data, key[0]) != position(data, reference_id[0])
        ):
            reasons.append("outside the same known broad position")
        candidate = _profile(player, peer_ids, peers, mode)
        pair = _pair(reference, candidate, issues, reasons)
        if pair.similarity is None:
            exclusions.append((key, pair.reasons))
        else:
            matches.append(pair)
    matches.sort(key=lambda pair: (-pair.similarity, *pair.candidate.player_team_id))
    return SimilarProfiles(
        reference,
        _basis(reference),
        tuple(matches[:5]),
        tuple(exclusions),
        tuple(issues),
    )


def pair_rows(pair: ProfilePair) -> list[dict]:
    """Raw differences are B minus A; unavailable values never become zero."""
    return [
        {
            "Metric": LABELS[a.metric],
            "A": a.value,
            "B": b.value,
            "A percentile": a.percentile,
            "B percentile": b.percentile,
            "B − A": b.value - a.value
            if a.value is not None and b.value is not None
            else None,
            "Peers": a.peer_count,
        }
        for a, b in zip(pair.reference.features, pair.candidate.features, strict=True)
    ]
