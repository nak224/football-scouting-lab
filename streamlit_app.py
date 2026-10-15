"""Local scouting interface. Run: python -m streamlit run streamlit_app.py"""

from dataclasses import asdict

import streamlit as st

from football_scouting_lab import ui_data
from football_scouting_lab.recruitment import rank_replacements
from football_scouting_lab.roles import (
    ROLE_TEMPLATES,
    EligibilityThresholds,
    assess_eligibility,
    normalize_weights,
)
from football_scouting_lab.similarity import STYLE_METRICS

ROLE_NAMES = {
    "deep_lying_playmaker": "Deep-Lying Playmaker",
    "ball_winning_midfielder": "Ball-Winning Midfielder",
}


@st.cache_data(max_entries=1, show_spinner="Loading season and calculating metrics…")
def load_cached(directory, fingerprint):
    # fingerprint is deliberately hashed: file changes invalidate the derived snapshot.
    return ui_data.load_scouting_data(directory)


def table(rows):
    formats = {
        name: st.column_config.NumberColumn(format="%.2f")
        for name in (rows[0] if rows else ())
        if any(
            part in name.lower()
            for part in ("score", "similarity", "fit", "minutes", "%", "/90", "points")
        )
    }
    st.dataframe(rows, hide_index=True, width="stretch", column_config=formats)


def player_explorer(data):
    st.subheader("Player explorer")
    search, team_filter, review_filter = st.columns([2, 2, 1])
    query = (
        search.text_input("Search player name", key="player_search").strip().casefold()
    )
    teams = sorted({row.team_id for row in data.metrics.players})
    team = team_filter.selectbox(
        "Historical team",
        [None, *teams],
        format_func=lambda key: (
            "All teams" if key is None else data.team_names.get(key, str(key))
        ),
    )
    reviewed = review_filter.checkbox("Reviewed demo only")
    rows = [
        row
        for row in ui_data.explorer_rows(data)
        if query in row["Player"].casefold()
        and (team is None or row["Team ID"] == team)
        and (not reviewed or row["Position review"] == "Reviewed demo midfielder")
    ]
    st.caption(
        f"{len(rows)} player/team rows · Initially sorted by rated minutes; click a column to sort. "
        "Transfers remain separate historical team rows. Unverified position ≠ eligible central midfielder."
    )
    if rows:
        table(rows)
    else:
        st.info("No players match these filters.")
    st.caption(
        "All displayed metrics use rated matches with positive estimated minutes. "
        "Coverage = rated recorded appearances / all recorded appearances; it is not event completeness. "
        "Blank values are unavailable, not zero. Minutes use approximate observed period ends."
    )
    with st.expander("Data coverage and limitations"):
        metrics = data.metrics
        usable = sum(row.duration_minutes is not None for row in metrics.matches)
        st.write(
            {
                "Matches with usable period durations": usable,
                "Matches without usable period durations": len(metrics.matches)
                - usable,
                "Unknown-player events (player ID 0)": len(
                    metrics.unknown_player_event_ids
                ),
                "Events with missing player metadata": len(
                    metrics.missing_player_metadata_event_ids
                ),
                "Events without a recorded appearance": len(
                    metrics.non_appearance_event_ids
                ),
                "Pass events with ambiguous outcomes": len(
                    metrics.ambiguous_pass_event_ids
                ),
                "Defensive duels with ambiguous outcomes": len(
                    metrics.ambiguous_defensive_duel_event_ids
                ),
            }
        )
        st.write(
            "Missing or ambiguous minutes exclude matches from rates and can bias comparisons. "
            "Raw accurate-pass/duel counts include only explicitly classified successes; "
            "ambiguous outcomes make affected rates unavailable. Review the local data provenance "
            "and docs/metrics.md before interpreting results."
        )


def metric_weights(role):
    with st.expander("Metric weights", expanded=False):
        st.caption(
            "Relative nonnegative weights; each component is normalized separately. Zero disables a feature."
        )
        style_column, role_column = st.columns(2)
        style_column.markdown("**Playing style**")
        style = {
            metric: style_column.number_input(
                ui_data.METRIC_LABELS[metric],
                min_value=0.0,
                value=25.0,
                step=5.0,
                key=f"style_weight_{metric}",
            )
            for metric in STYLE_METRICS
        }
        role_column.markdown("**Tactical role**")
        weights = {
            metric: role_column.number_input(
                ui_data.METRIC_LABELS[metric],
                min_value=0.0,
                value=100.0 * weight,
                step=5.0,
                key=f"role_weight_{role}_{metric}",
            )
            for metric, weight in ROLE_TEMPLATES[role].items()
        }
    return style, weights


def explain_result(data, result):
    reference = result.style.reference
    st.caption(
        f"Reference: {data.label(result.reference_id)} · {reference.player.rated_minutes:.1f} rated minutes · "
        f"{reference.rated_matches}/{reference.recorded_appearances} appearances rated "
        f"({100 * reference.appearance_coverage:.1f}% coverage)."
    )
    st.warning(
        "Small demonstration sample: only four reviewed players are available, "
        "with at most three replacements before further exclusions. Rankings are not league-wide."
    )
    st.caption(
        f"Style normalization: {len(result.style.normalization_ids)} complete player/team rows · "
        f"Role normalization: {len(result.role.reference_ids)} complete rows. "
        "These populations may differ. Scores are cohort-relative, not probabilities."
    )
    for warning in (*result.style.warnings, *result.warnings):
        st.warning(warning)
    if result.shortlist:
        table(ui_data.shortlist_rows(data, result))
        options = [row.candidate_id for row in result.shortlist]
        if st.session_state.get("explain_candidate") not in options:
            st.session_state.pop("explain_candidate", None)
        selected = st.selectbox(
            "Explain candidate",
            options,
            format_func=data.label,
            key="explain_candidate",
        )
        candidate = next(
            row for row in result.shortlist if row.candidate_id == selected
        )
        st.write(
            f"Style {candidate.style.score:.2f} × {result.style_priority:.2f} "
            f"= {candidate.style_contribution:.2f} points; "
            f"role {candidate.role.score:.2f} × {1 - result.style_priority:.2f} "
            f"= {candidate.role_contribution:.2f} points. "
            f"Combined: **{candidate.combined_score:.2f} / 100**."
        )
        with st.expander("Feature-level explanations", expanded=True):
            st.markdown("**Style similarity**")
            st.caption(
                "Each feature uses the style cohort's minimum and maximum. "
                "Similarity = 100 × (1 − weighted absolute distance). Constant features contribute zero distance."
            )
            table(
                [
                    {
                        "Feature": ui_data.METRIC_LABELS[row.metric],
                        **{
                            key.replace("_", " ").capitalize(): value
                            for key, value in asdict(row).items()
                            if key != "metric"
                        },
                    }
                    for row in candidate.style.differences
                ]
            )
            st.markdown("**Role fit**")
            st.caption(
                "Weighted percentile points within the role cohort; constant features score 50."
            )
            table(
                [
                    {
                        "Feature": ui_data.METRIC_LABELS[row.metric],
                        "Measurement": row.measurement,
                        "Percentile": row.percentile,
                        "Weight": row.weight,
                        "Points": row.points,
                    }
                    for row in candidate.role.contributions
                ]
            )
            notes = sorted(
                {
                    note
                    for match in candidate.style.candidate.player.matches
                    for note in match.warnings
                }
            )
            if notes:
                st.write("Minutes and measurement notes", notes)
    else:
        st.info(
            "The shortlist is empty. Review exclusions, thresholds and shortlist length."
        )
    with st.expander("Normalization, position reviews and exclusions"):
        left, right = st.columns(2)
        for column, title, weights, ids in (
            (left, "Style", result.style.weights, result.style.normalization_ids),
            (right, "Role", result.role.weights, result.role.reference_ids),
        ):
            column.markdown(f"**{title} normalization cohort**")
            column.write([data.label(key) for key in ids])
            column.write(
                {ui_data.METRIC_LABELS[key]: value for key, value in weights.items()}
            )
        st.write(
            "Style feature ranges",
            {
                ui_data.METRIC_LABELS[key]: value
                for key, value in result.style.feature_ranges.items()
            },
        )
        table(
            [
                {
                    "Player / historical team": data.label(row.candidate_id),
                    "Style similarity": row.style.score,
                    "Role fit": row.role.score,
                    "Reasons": "; ".join(row.reasons),
                }
                for row in result.candidates
                if row.reasons
            ]
        )
        table(
            [
                {
                    "Player / historical team": data.label(key),
                    "Review note": review.note,
                    "Evidence": review.evidence,
                }
                for key, review in ui_data.present_reviews(data).items()
            ]
        )


def replacement_finder(data):
    st.subheader("Replacement finder")
    first, second, third = st.columns(3)
    role = first.selectbox(
        "Tactical role", list(ROLE_NAMES), format_func=ROLE_NAMES.get, key="role"
    )
    minimum = second.number_input(
        "Minimum rated minutes",
        min_value=0.0,
        value=600.0,
        step=100.0,
        key="min_minutes",
    )
    coverage = third.slider(
        "Minimum appearance coverage %", 0, 100, 60, key="min_coverage"
    )
    priority = st.slider(
        "Style priority",
        0.0,
        1.0,
        0.5,
        0.05,
        key="style_priority",
        help="0 = role only; 1 = style only. Both source scores must be available.",
    )
    limit = st.number_input(
        "Shortlist length",
        min_value=0,
        max_value=20,
        value=3,
        step=1,
        key="shortlist_length",
    )
    style_weights, role_weights = metric_weights(role)
    thresholds = EligibilityThresholds(minimum, coverage / 100)
    try:
        normalize_weights(role, role_weights)
        options = ui_data.reference_options(data, thresholds, style_weights)
        if not options:
            st.info(
                "No reviewed reference has eligible minutes, coverage and complete selected style metrics. Try lower thresholds."
            )
            table(
                [
                    {
                        "Player / historical team": data.label(
                            (row.player.player_id, row.player.team_id)
                        ),
                        "Eligibility": "; ".join(row.reasons)
                        or "Eligible; selected style measurements may be missing",
                    }
                    for row in assess_eligibility(
                        data.metrics.players, ui_data.present_reviews(data), thresholds
                    )
                    if row.review.status == "included"
                ]
            )
            return
        if st.session_state.get("reference") not in options:
            st.session_state.pop("reference", None)
        default = options.index((224677, 2447)) if (224677, 2447) in options else 0
        reference = st.selectbox(
            "Reference player / historical team",
            options,
            index=default,
            format_func=data.label,
            key="reference",
        )
        result = rank_replacements(
            data.metrics.players,
            ui_data.present_reviews(data),
            reference,
            role,
            style_priority=priority,
            style_weights=style_weights,
            role_weights=role_weights,
            thresholds=thresholds,
            limit=limit,
        )
    except ValueError as error:
        st.warning(f"Check ranking configuration: {error}")
        return
    explain_result(data, result)


def main():
    st.set_page_config(
        page_title="Football Scouting Lab", page_icon="⚽", layout="wide"
    )
    st.title("Football Scouting Lab")
    st.caption("Bundesliga 2017/18 · Historical recruitment analysis")
    st.info(
        "Limited demonstration: only four reviewed midfielders. Their CM/CDM position proxies "
        "are not exhaustive tactical-position ground truth. Other players remain unverified."
    )
    with st.sidebar:
        st.header("Local season data")
        st.caption(
            "Supply your own four Wyscout JSON files. Nothing is downloaded or uploaded to an external service."
        )
        with st.form("data_source"):
            directory = st.text_input("Local data directory", key="data_dir")
            submitted = st.form_submit_button("Load season")
        if submitted:
            st.session_state["loaded_directory"] = directory
            load_cached.clear()
        st.caption("Use Load season to force a refresh after replacing source files.")
    if "loaded_directory" not in st.session_state:
        st.info(
            "Enter the directory containing matches_Germany.json, players.json, teams.json and events_Germany.json, then select Load season."
        )
        return
    try:
        root, fingerprint = ui_data.dataset_key(st.session_state["loaded_directory"])
        data = load_cached(root, fingerprint)
    except (OSError, ValueError) as error:
        st.error(f"Could not load local season: {error}")
        return
    matches, players, events = st.columns(3)
    matches.metric("Matches", len(data.metrics.matches))
    players.metric("Player / historical team rows", len(data.metrics.players))
    events.metric("Events", f"{data.metrics.event_count:,}")
    explorer, replacements = st.tabs(["Player explorer", "Replacement finder"])
    with explorer:
        player_explorer(data)
    with replacements:
        replacement_finder(data)


if __name__ == "__main__":
    main()
