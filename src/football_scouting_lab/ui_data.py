"""Small presentation helpers; no Streamlit dependency or scoring algorithms."""

import re
from dataclasses import dataclass
from pathlib import Path
from tempfile import TemporaryDirectory

from .demo_cohort import DEMO_REVIEWS
from .fictional_data import REVIEWS as FICTIONAL_REVIEWS
from .fictional_data import VERSION as FICTIONAL_VERSION
from .fictional_data import write_fictional_data
from .metrics import PlayerSeasonMetrics, SeasonMetrics, calculate_metrics
from .recruitment import RecruitmentRanking
from .roles import EligibilityThresholds, assess_eligibility
from .similarity import compare_styles, normalize_style_weights
from .team_fit import MidfieldComparison, prepare_player_profile
from .wyscout import load_events, load_season

DATA_FILES = (
    "matches_Germany.json",
    "players.json",
    "teams.json",
    "events_Germany.json",
)
METRIC_LABELS = {
    "pass_attempts_per90": "Pass attempts /90",
    "accurate_passes_per90": "Accurate passes /90",
    "pass_completion_pct": "Pass completion %",
    "interceptions_per90": "Interceptions /90",
    "successful_defensive_duels_per90": "Successful defensive duels /90",
}


@dataclass(frozen=True)
class ScoutingData:
    """Derived metrics and names only; callers treat this snapshot as read-only.

    Streamlit's data cache returns independent copies, including nested mappings.
    Raw event records are intentionally not retained here.
    """

    metrics: SeasonMetrics
    player_names: dict[int, str]
    team_names: dict[int, str]
    fictional: bool = False

    def label(self, key: tuple[int, int]) -> str:
        player, team = key
        return (
            f"{self.player_names.get(player, f'Player {player}')} · "
            f"{self.team_names.get(team, f'Team {team}')} ({player}/{team})"
        )


def dataset_key(directory: str) -> tuple[str, tuple[tuple[str, int, int], ...]]:
    """Cheap cache invalidation on file size/mtime; explicit reload also clears it."""
    if not directory.strip():
        raise ValueError("Enter the local directory containing the four JSON files.")
    root = Path(directory).expanduser().resolve()
    stamps = []
    for name in DATA_FILES:
        path = root / name
        if not path.is_file():
            raise ValueError(f"Missing data file: {path}")
        stat = path.stat()
        stamps.append((name, stat.st_size, stat.st_mtime_ns))
    return str(root), tuple(stamps)


def display_text(text: str) -> str:
    """Decode literal source Unicode escapes without corrupting actual accents."""
    return re.sub(r"\\+u([0-9a-fA-F]{4})", lambda m: chr(int(m[1], 16)), text)


def load_scouting_data(directory: str) -> ScoutingData:
    metadata = load_season(Path(directory))
    markers = [match.get("fictionalDemo") for match in metadata.matches.values()]
    fictional = FICTIONAL_VERSION in markers
    if fictional and not all(marker == FICTIONAL_VERSION for marker in markers):
        raise ValueError(
            "FICTIONAL demo matches cannot be mixed with unmarked season data"
        )
    events = load_events(Path(directory), metadata)
    metrics = calculate_metrics(metadata, events)
    player_ids = {row.player_id for row in metrics.players}
    names = {}
    for player_id in player_ids:
        record = metadata.players.get(player_id, {})
        name = (
            record.get("shortName")
            or " ".join(
                str(record.get(part, "")) for part in ("firstName", "lastName")
            ).strip()
        )
        names[player_id] = display_text(str(name or f"Player {player_id}"))
    teams = {
        team_id: display_text(str(record.get("name") or f"Team {team_id}"))
        for team_id, record in metadata.teams.items()
    }
    return ScoutingData(metrics, names, teams, fictional=fictional)


def load_fictional_demo() -> ScoutingData:
    """Generate temporary raw files and reuse the real loading/analytics pipeline."""
    with TemporaryDirectory(prefix="football-scouting-fictional-") as directory:
        write_fictional_data(directory)
        return load_scouting_data(directory)


def configured_reviews(data: ScoutingData):
    return FICTIONAL_REVIEWS if data.fictional else DEMO_REVIEWS


def present_reviews(data: ScoutingData):
    """Keep fictional assignments separate from the four real-data demo reviews."""
    keys = {(row.player_id, row.team_id) for row in data.metrics.players}
    return {
        key: value for key, value in configured_reviews(data).items() if key in keys
    }


def explorer_rows(data: ScoutingData) -> list[dict]:
    """Fresh display rows; unknown counts, minutes and rates remain None."""
    rows = []
    for eligibility in assess_eligibility(data.metrics.players, present_reviews(data)):
        player = eligibility.player
        counts = player.rated
        rows.append(
            {
                "Player": data.player_names[player.player_id],
                "Historical team": data.team_names.get(
                    player.team_id, f"Team {player.team_id}"
                ),
                "Player ID": player.player_id,
                "Team ID": player.team_id,
                "Position review": (
                    (
                        "Fictional demo midfielder"
                        if data.fictional
                        else "Reviewed demo midfielder"
                    )
                    if eligibility.review.status == "included"
                    else f"{eligibility.review.status.capitalize()} position"
                ),
                "Rated minutes": player.rated_minutes,
                "Coverage %": (
                    100 * eligibility.appearance_coverage
                    if eligibility.appearance_coverage is not None
                    else None
                ),
                "Rated matches": eligibility.rated_matches,
                "Recorded appearances": eligibility.recorded_appearances,
                "Unrecorded event matches": eligibility.unrecorded_event_matches,
                "Pass attempts (rated)": counts.pass_attempts if counts else None,
                "Accurate passes (rated)": counts.accurate_passes if counts else None,
                "Interceptions (rated)": counts.interceptions if counts else None,
                "Successful defensive duels (rated)": (
                    counts.successful_defensive_duels if counts else None
                ),
                "Pass completion %": counts.pass_completion_pct if counts else None,
                **{
                    METRIC_LABELS[f"{metric}_per90"]: value if counts else None
                    for metric, value in player.per90.items()
                },
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


def reference_options(data: ScoutingData, thresholds: EligibilityThresholds, weights):
    """Ask the existing style API which eligible rows have complete measurements."""
    normalize_style_weights(weights)  # Surface configuration errors, not an empty pool.
    reviews = present_reviews(data)
    for row in assess_eligibility(data.metrics.players, reviews, thresholds):
        if row.eligible:
            key = (row.player.player_id, row.player.team_id)
            try:
                return compare_styles(
                    data.metrics.players,
                    reviews,
                    key,
                    weights=weights,
                    thresholds=thresholds,
                ).normalization_ids
            except ValueError:
                # This reference lacks required style measurements; try another.
                continue
    return ()


def shortlist_rows(data: ScoutingData, result: RecruitmentRanking) -> list[dict]:
    rows = []
    for candidate in result.shortlist:
        player_id, team_id = candidate.candidate_id
        eligibility = candidate.style.candidate
        rows.append(
            {
                "Player": data.player_names[player_id],
                "Historical team": data.team_names.get(team_id, f"Team {team_id}"),
                "Player ID": player_id,
                "Team ID": team_id,
                "Combined score": candidate.combined_score,
                "Style similarity": candidate.style.score,
                "Role fit": candidate.role.score,
                "Style points": candidate.style_contribution,
                "Role points": candidate.role_contribution,
                "Rated minutes": eligibility.player.rated_minutes,
                "Coverage %": 100 * eligibility.appearance_coverage,
                "Rated matches": eligibility.rated_matches,
                "Recorded appearances": eligibility.recorded_appearances,
            }
        )
    return rows


def midfield_cohort(
    data: ScoutingData, thresholds: EligibilityThresholds
) -> tuple[tuple[PlayerSeasonMetrics, ...], list[dict]]:
    """Select complete reviewed rows before comparing ANY lineups or weights.

    Backend profile validation supplies completeness checks; no normalization or
    scoring is performed here. Missing reviewed entries stay explicit exclusions.
    """
    reviews = present_reviews(data)
    cohort, exclusions = [], []
    for candidate in assess_eligibility(data.metrics.players, reviews, thresholds):
        key = (candidate.player.player_id, candidate.player.team_id)
        if key not in reviews:
            continue
        reasons = list(candidate.reasons)
        if not reasons:
            try:
                prepare_player_profile(candidate.player)
            except ValueError as error:
                reasons.append(str(error))
        if reasons:
            exclusions.append(
                {
                    "Player / historical team": data.label(key),
                    "Exclusion reason": "; ".join(reasons),
                }
            )
        else:
            cohort.append(candidate.player)
    for key in sorted(configured_reviews(data).keys() - reviews.keys()):
        exclusions.append(
            {
                "Player / historical team": f"Unavailable demo entry {key[0]}/{key[1]}",
                "Exclusion reason": "player/team row absent from local metrics",
            }
        )
    return tuple(cohort), exclusions


def midfield_feature_rows(result: MidfieldComparison) -> list[dict]:
    """Display backend measurements/contributions unchanged; coverage uses [0, 1]."""
    return [
        {
            "Feature": METRIC_LABELS[feature.metric],
            "Before coverage": feature.before_coverage,
            "After coverage": feature.after_coverage,
            "Coverage change": feature.coverage_change,
            "Before raw mean": feature.before_mean,
            "After raw mean": feature.after_mean,
            "Weighted contribution (points)": feature.weighted_change,
        }
        for feature in result.features
    ]
