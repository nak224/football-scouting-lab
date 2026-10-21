"""Local scouting interface. Run: python -m streamlit run streamlit_app.py"""

from dataclasses import asdict

import streamlit as st

from football_scouting_lab import ui_data
from football_scouting_lab.fictional_data import BASELINE as FICTIONAL_BASELINE
from football_scouting_lab.fictional_data import CANDIDATE as FICTIONAL_CANDIDATE
from football_scouting_lab.fictional_data import VERSION as FICTIONAL_VERSION
from football_scouting_lab.recruitment import rank_replacements
from football_scouting_lab.roles import (
    ROLE_TEMPLATES,
    EligibilityThresholds,
    assess_eligibility,
    normalize_weights,
)
from football_scouting_lab.similarity import STYLE_METRICS
from football_scouting_lab.team_fit import PROFILE_METRICS, compare_midfield

ROLE_NAMES = {
    "deep_lying_playmaker": "Deep-Lying Playmaker",
    "ball_winning_midfielder": "Ball-Winning Midfielder",
}


@st.cache_data(max_entries=1, show_spinner="Loading season and calculating metrics…")
def load_cached(directory, fingerprint):
    # fingerprint is deliberately hashed: file changes invalidate the derived snapshot.
    return ui_data.load_scouting_data(directory)


@st.cache_data(max_entries=1, show_spinner="Generating fictional demo…")
def load_demo_cached(version):
    return ui_data.load_fictional_demo()


def activate_source(mode):
    """Give each source a clean set of analysis controls, without mixing data."""
    controls = {
        "player_search",
        "reference",
        "explain_candidate",
        "role",
        "min_minutes",
        "min_coverage",
        "style_priority",
        "shortlist_length",
        "cohort_only",
    }
    for key in list(st.session_state):
        if key in controls or key.startswith(
            ("style_weight_", "role_weight_", "midfield_")
        ):
            st.session_state.pop(key)
    st.session_state["data_mode"] = mode


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
    reviewed = review_filter.checkbox(
        "Fictional cohort only" if data.fictional else "Included reviews only",
        key="cohort_only",
    )
    included = {
        key
        for key, review in ui_data.present_reviews(data).items()
        if review.status == "included"
    }
    rows = [
        row
        for row in ui_data.explorer_rows(data)
        if query in row["Player"].casefold()
        and (team is None or row["Team ID"] == team)
        and (not reviewed or (row["Player ID"], row["Team ID"]) in included)
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
    st.caption(
        "Rankings are relative to the supplied reviewed cohort; sample sizes and exclusions "
        "limit their interpretation. Historical team rows are kept separate."
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
        preferred = FICTIONAL_BASELINE[1] if data.fictional else (224677, 2447)
        default = options.index(preferred) if preferred in options else 0
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


def midfield_select(data, label, key, options, preferred):
    """Repair stale/duplicate selections before Streamlit renders a changed pool."""
    if key in st.session_state and st.session_state[key] not in options:
        st.session_state.pop(key)
        st.caption(f"{label} selection updated to match the available players.")
    return st.selectbox(
        label,
        options,
        index=options.index(preferred) if preferred in options else 0,
        format_func=data.label,
        key=key,
    )


def midfield_result(data, result):
    st.metric(
        "Signed weighted coverage change",
        f"{result.weighted_coverage_change:+.2f} points",
    )
    st.caption(
        "Descriptive profile representation only. Positive means increased weighted coverage; "
        "opposing feature changes can cancel. This is not a team-performance prediction or rating."
    )
    before, after = st.columns(2)
    for column, title, lineup, change in (
        (before, "BEFORE", result.baseline_lineup, "Removed"),
        (after, "AFTER", result.updated_lineup, "Added"),
    ):
        with column:
            st.markdown(f"**{title} · Hypothetical 4-3-3 midfield**")
            table(
                [
                    {
                        "Slot": slot,
                        "Player / historical team": data.label(key),
                        "Change": change
                        if slot == result.replacement_slot
                        else "Retained",
                    }
                    for slot, key in enumerate(lineup)
                ]
            )
    st.markdown(
        f"**Removed:** {data.label(result.replaced_id)}  \n"
        f"**Added:** {data.label(result.candidate_id)}"
    )
    feature_rows = ui_data.midfield_feature_rows(result)
    st.dataframe(
        feature_rows,
        hide_index=True,
        width="stretch",
        column_config={
            name: st.column_config.NumberColumn(format="%.3f")
            for name in feature_rows[0]
            if name != "Feature"
        },
    )
    st.caption(
        "Coverage is the strongest individual feature representation on the fixed cohort's 0–1 scale. "
        "Raw means average the three individuals; completion is not pooled team pass completion. "
        "Weighted contribution = 100 × normalized weight × coverage change."
    )
    for warning in result.warnings:
        if warning.startswith("tiny comparison cohort"):
            st.caption(warning)
        else:
            st.warning(warning)
    with st.expander("Simulator normalization, samples and warnings"):
        st.write(
            "Fixed comparison cohort IDs",
            [row.player_team_id for row in result.comparison_cohort],
        )
        table(
            [
                {
                    "Feature": ui_data.METRIC_LABELS[metric],
                    "Minimum": bounds[0],
                    "Maximum": bounds[1],
                    "Normalized weight": result.weights[metric],
                }
                for metric, bounds in result.feature_ranges.items()
            ]
        )
        table(
            [
                {
                    "Player / historical team": data.label(row.player_team_id),
                    "Rated minutes": row.player.rated_minutes,
                    "Rated matches": row.rated_matches,
                    "Recorded appearances": row.recorded_appearances,
                    "Appearance coverage %": 100 * row.appearance_coverage,
                    "Unrecorded event matches": row.unrecorded_event_matches,
                    "Source warnings": "; ".join(
                        sorted(
                            {
                                note
                                for match in row.player.matches
                                for note in match.warnings
                            }
                        )
                    ),
                }
                for row in result.comparison_cohort
            ]
        )
        for limitation in result.limitations:
            st.write(limitation)


def midfield_simulator(data, source_key):
    st.subheader("Midfield simulator")
    st.markdown(
        "**Hypothetical 4-3-3 midfield**, not an observed historical XI. Players from different clubs "
        "are not assumed to have played together. Only explicitly included, eligible reviews are considered."
    )
    selection_keys = [
        *(f"midfield_slot_{slot}" for slot in range(3)),
        "midfield_candidate",
    ]
    if st.session_state.get("midfield_source") != source_key:
        for key in selection_keys:
            st.session_state.pop(key, None)
        if "midfield_source" in st.session_state:
            st.caption(
                "Local data or reviews changed; simulator player selections have been reset."
            )
        st.session_state["midfield_source"] = source_key
    first, second = st.columns(2)
    minimum = first.number_input(
        "Simulator minimum rated minutes",
        min_value=0.0,
        value=600.0,
        step=100.0,
        key="midfield_min_minutes",
    )
    coverage = second.slider(
        "Simulator minimum appearance coverage %",
        0,
        100,
        60,
        key="midfield_min_coverage",
    )
    st.caption(
        "The same eligibility rules and defaults as Replacement finder apply here, with separate settings. "
        "Threshold changes can change the fixed cohort; lineup and weight changes cannot."
    )
    try:
        cohort, exclusions = ui_data.midfield_cohort(
            data, EligibilityThresholds(minimum, coverage / 100)
        )
    except ValueError as error:
        st.warning(f"Check simulator eligibility settings: {error}")
        return
    with st.expander("Simulator eligibility and exclusions", expanded=bool(exclusions)):
        st.caption(
            f"{len(cohort)} complete reviewed player/team rows available. Unverified players are excluded."
        )
        if exclusions:
            table(exclusions)
        else:
            st.write(
                f"All {len(cohort)} available reviewed entries meet these thresholds and have complete metrics."
            )
    options = [(row.player_id, row.team_id) for row in cohort]
    if len({key[0] for key in options}) < 4:
        for key in selection_keys:
            st.session_state.pop(key, None)
        st.warning(
            "Midfield simulator unavailable: at least four distinct reviewed players with eligible minutes, "
            "coverage and all four complete metrics are required. Review exclusions or lower thresholds."
        )
        return
    defaults = (
        FICTIONAL_BASELINE
        if data.fictional
        else ((3345, 2444), (224677, 2447), (289711, 2975))
    )
    baseline = []
    columns = st.columns(3)
    for slot, preferred in enumerate(defaults):
        available = [
            key
            for key in options
            if key[0] not in {selected[0] for selected in baseline}
        ]
        with columns[slot]:
            baseline.append(
                midfield_select(
                    data,
                    f"Baseline slot {slot}",
                    f"midfield_slot_{slot}",
                    available,
                    preferred,
                )
            )
    left, right = st.columns(2)
    if st.session_state.get("midfield_replace_slot") not in (0, 1, 2):
        st.session_state.pop("midfield_replace_slot", None)
    replacement_slot = left.selectbox(
        "Replacement slot", [0, 1, 2], index=2, key="midfield_replace_slot"
    )
    available = [
        key for key in options if key[0] not in {selected[0] for selected in baseline}
    ]
    with right:
        candidate = midfield_select(
            data,
            "Candidate replacement",
            "midfield_candidate",
            available,
            FICTIONAL_CANDIDATE if data.fictional else (20475, 2444),
        )
    with st.expander("Midfield profile weights"):
        st.caption(
            "Relative nonnegative weights, normalized by the comparison API. All four measurements remain required."
        )
        weights = {
            metric: st.number_input(
                ui_data.METRIC_LABELS[metric],
                min_value=0.0,
                value=25.0,
                step=5.0,
                key=f"midfield_weight_{metric}",
            )
            for metric in PROFILE_METRICS
        }
    try:
        result = compare_midfield(
            cohort, baseline, replacement_slot, candidate, weights=weights
        )
    except ValueError as error:
        st.warning(f"Check simulator configuration: {error}")
        return
    midfield_result(data, result)


def main():
    st.set_page_config(
        page_title="Football Scouting Lab", page_icon="⚽", layout="wide"
    )
    st.title("Football Scouting Lab")
    st.caption(
        "Explainable player exploration, recruitment rankings and hypothetical midfield comparison"
    )
    with st.sidebar:
        st.header("Choose data")
        if st.button("Load FICTIONAL demo", key="load_demo", type="primary"):
            activate_source("fictional")
        st.caption(
            "Invented players, clubs and events. No files or downloads required."
        )
        with st.expander("Use local Wyscout files"):
            with st.form("data_source"):
                directory = st.text_input("Local data directory", key="data_dir")
                review_file = st.text_input(
                    "Optional local review JSON file",
                    key="review_file",
                    help="Blank uses the four default reviews. A supplied file replaces them; omitted players stay unverified.",
                )
                force_reload = st.checkbox("Force source reload", key="force_reload")
                submitted = st.form_submit_button("Load season", key="load_season")
            if submitted:
                if (
                    st.session_state.get("data_mode") != "local"
                    or st.session_state.get("loaded_directory") != directory
                ):
                    activate_source("local")
                st.session_state["loaded_directory"] = directory
                st.session_state["loaded_review_file"] = review_file
                if force_reload:
                    load_cached.clear()
            st.caption(
                "Files stay outside Git. Load season applies reviews without reprocessing unchanged data. "
                "Force source reload recalculates metrics. Reviews are ignored in the fictional demo."
            )
    mode = st.session_state.get("data_mode")
    if mode is None:
        st.info(
            "Select Load FICTIONAL demo in the sidebar to try all three sections without downloading data, or supply your own local Wyscout files."
        )
        return
    try:
        if mode == "fictional":
            data = load_demo_cached(FICTIONAL_VERSION)
            source_key = ("fictional", FICTIONAL_VERSION)
        else:
            root, fingerprint = ui_data.dataset_key(
                st.session_state["loaded_directory"]
            )
            data = load_cached(root, fingerprint)
            data = ui_data.apply_review_file(
                data, st.session_state.get("loaded_review_file", "")
            )
            source_key = (root, fingerprint, ui_data.review_key(data))
    except (OSError, ValueError) as error:
        st.error(
            f"Could not load {'fictional demo' if mode == 'fictional' else 'local season'}: {error}"
        )
        return
    if data.fictional:
        st.warning(
            "FICTIONAL DEMO — All players, clubs, matches, events and results are invented. NOT real Bundesliga statistics. Four midfielders are assigned for this fixture only."
        )
        st.sidebar.markdown("**Active: FICTIONAL demo**")
    else:
        st.caption("Local Wyscout Bundesliga 2017/18 data")
        if data.custom_reviews is None:
            st.info(
                "Limited demonstration: only four reviewed midfielders. Their CM/CDM position proxies are not exhaustive tactical-position ground truth. Other players remain unverified."
            )
        else:
            st.info(
                "External manual reviews are active. Evidence is recorded, not independently verified. "
                "Omitted players remain unverified; no positions are inferred."
            )
        st.sidebar.markdown("**Active: local Wyscout files**")
    reviews = ui_data.configured_reviews(data)
    unverified = sum(
        (row.player_id, row.team_id) not in reviews for row in data.metrics.players
    )
    st.caption(
        f"Cohort decisions: {sum(r.status == 'included' for r in reviews.values())} included · "
        f"{sum(r.status == 'excluded' for r in reviews.values())} excluded · "
        f"{unverified} unverified metric rows · {len({player for player, _ in reviews})} reviewed player IDs. "
        "Decisions are scoped to player / historical team."
    )
    matches, players, events = st.columns(3)
    matches.metric("Matches", len(data.metrics.matches))
    players.metric("Player / historical team rows", len(data.metrics.players))
    events.metric("Events", f"{data.metrics.event_count:,}")
    explorer, replacements, midfield = st.tabs(
        ["Player explorer", "Replacement finder", "Midfield simulator"]
    )
    with explorer:
        player_explorer(data)
    with replacements:
        replacement_finder(data)
    with midfield:
        midfield_simulator(data, source_key)
    with st.expander("Cohort reviews and evidence"):
        rows = ui_data.review_rows(data)
        if rows:
            table(rows)
        else:
            st.info(
                "The supplied review set is empty. No player is included for scoring."
            )


if __name__ == "__main__":
    main()
