"""Small Explorer comparison workflow; no recruitment scoring or new services."""

import hashlib

import streamlit as st

from . import explorer
from .ui_data import POSITION_GROUPS

METHOD = (
    "One fixed source population with at least 600 rated minutes. Same position uses A's "
    "known broad role; choose All players for cross-position comparison. Similarity is "
    "100 minus the mean absolute percentile difference, not quality, role fit or probability."
)


def open_comparison(data, reference, view):
    if st.session_state.get("explorer_pair_reference") != reference:
        for key in list(st.session_state):
            if key.startswith("explorer_pair_"):
                st.session_state.pop(key)
        st.session_state["explorer_pair_reference"] = reference
        st.session_state["explorer_pair_mode_saved"] = (
            "All players"
            if explorer.position(data, reference[0]) == "Unknown"
            else st.session_state.get("explorer_profile_mode", "Same position")
        )
    st.session_state["explorer_view"] = view
    st.session_state["explorer_pair_picking"] = (
        view == "compare" and st.session_state.get("explorer_pair_second") is None
    )


def _profile():
    st.session_state["explorer_view"] = "profile"


def _pick():
    st.session_state["explorer_pair_picking"] = True
    st.session_state["explorer_view"] = "compare"


def _choose(rows, context):
    token = hashlib.sha256(repr(context).encode()).hexdigest()[:20]
    selection = st.dataframe(
        rows,
        key=f"explorer_pair_rows_{token}",
        hide_index=True,
        width="stretch",
        on_select="rerun",
        selection_mode="single-row",
        height=min(290, 40 + 36 * len(rows)),
        column_config={
            "Player ID": None,
            "Team ID": None,
            "Rated minutes": st.column_config.NumberColumn(format="%.0f"),
            "Descriptive similarity": st.column_config.NumberColumn(
                format="%.1f", help=METHOD
            ),
        },
    )
    selected = explorer.selected_player(rows, selection.selection.rows)
    if selected is not None:
        st.session_state["explorer_pair_epoch"] = (
            st.session_state.get("explorer_pair_epoch", 0) + 1
        )
        st.session_state["explorer_pair_second"] = selected
        st.session_state["explorer_pair_picking"] = False
        st.session_state["explorer_view"] = "compare"
        st.rerun()


def _name(data, key):
    return data.player_names.get(key[0], f"Player {key[0]}")


def _club(data, key):
    return data.team_names.get(key[1], f"Team {key[1]}")


def _suggestions(data, reference, result, context):
    st.markdown("**Suggested similar players**")
    st.caption(
        f"{len(result.matches)} suggestions · Descriptive similarity, 0–100 · Select a row to compare"
    )
    rows = []
    players = {(row.player_id, row.team_id): row for row in data.metrics.players}
    for pair in result.matches:
        key = pair.candidate.player_team_id
        rows.append(
            {
                "Name": _name(data, key),
                "Historical team": _club(data, key),
                "Position": explorer.position(data, key[0]),
                "Descriptive similarity": pair.similarity,
                "Rated minutes": players[key].rated_minutes,
                "Player ID": key[0],
                "Team ID": key[1],
            }
        )
    if rows:
        _choose(rows, (reference, result.reference.mode, "suggestions", context))
    else:
        st.info(
            result.warnings[0]
            if result.warnings
            else "No similar players have a sufficient sample and complete comparison features."
        )


def _picker(data, reference, mode, result, context):
    st.markdown("**Choose player B**")
    saved = st.session_state.get("explorer_pair_filters", {})
    for key, default in (
        ("explorer_pair_query", ""),
        ("explorer_pair_team", None),
        ("explorer_pair_position", None),
    ):
        if key not in st.session_state:
            st.session_state[key] = saved.get(key, default)
    source_rows = explorer.discovery_rows(data)
    allowed = [
        row
        for row in source_rows
        if row["Player ID"] != reference[0]
        and (
            mode == "All players"
            or row["Position"] == explorer.position(data, reference[0]) != "Unknown"
        )
    ]
    name, league, club, position = st.columns([1.5, 1.2, 1.3, 1])
    query = name.text_input(
        "Player B name", key="explorer_pair_query", placeholder="Search players…"
    )
    league.selectbox(
        "League", [explorer.LEAGUE], disabled=True, key="explorer_pair_league"
    )
    teams = sorted(
        {row["Team ID"] for row in allowed},
        key=lambda key: data.team_names.get(key, str(key)),
    )
    if st.session_state["explorer_pair_team"] not in (None, *teams):
        st.session_state["explorer_pair_team"] = None
    team = club.selectbox(
        "Historical team",
        [None, *teams],
        key="explorer_pair_team",
        placeholder="All teams",
        format_func=lambda key: (
            "All teams" if key is None else data.team_names.get(key, str(key))
        ),
    )
    groups = [
        None,
        *(
            group
            for group in (*POSITION_GROUPS, "Unknown")
            if any(row["Position"] == group for row in allowed)
        ),
    ]
    if st.session_state["explorer_pair_position"] not in groups:
        st.session_state["explorer_pair_position"] = None
    group = position.selectbox(
        "Position",
        groups,
        key="explorer_pair_position",
        placeholder="All positions",
        format_func=lambda value: value or "All positions",
    )
    st.session_state["explorer_pair_filters"] = {
        "explorer_pair_query": query,
        "explorer_pair_team": team,
        "explorer_pair_position": group,
    }
    if query.strip() or team is not None or group is not None or not result.matches:
        rows = [
            {
                key: row[key]
                for key in (
                    "Name",
                    "Historical team",
                    "Position",
                    "Rated minutes",
                    "Player ID",
                    "Team ID",
                )
            }
            for row in allowed
            if query.strip().casefold() in row["Name"].casefold()
            and (team is None or row["Team ID"] == team)
            and (group is None or row["Position"] == group)
        ]
        if rows:
            st.caption("Search results · Select a row to compare")
            _choose(rows, (reference, mode, "search", context, query, team, group))
        else:
            st.info("No players match these filters.")
    _suggestions(data, reference, result, context)


def _sample_card(data, key, title):
    player = next(
        row for row in data.metrics.players if (row.player_id, row.team_id) == key
    )
    rated = sum(
        match.appearance_recorded and match.rate_eligible for match in player.matches
    )
    appearances = sum(match.appearance_recorded for match in player.matches)
    minutes = player.rated_minutes
    with st.container(border=True):
        st.caption(title)
        st.markdown(f"**{_name(data, key)}**")
        st.caption(
            f"{_club(data, key)} · {explorer.position(data, key[0])} · {explorer.SEASON}"
        )
        st.caption(
            f"{minutes:,.0f} rated min · {rated}/{appearances} appearances rated"
            if minutes is not None
            else f"Minutes unavailable · {rated}/{appearances} appearances rated"
        )


def _pair_view(data, pair, chart):
    left, right = st.columns(2)
    with left:
        _sample_card(data, pair.reference.player_team_id, "PLAYER A")
    with right:
        _sample_card(data, pair.candidate.player_team_id, "PLAYER B")
    if pair.similarity is not None:
        st.metric("Descriptive similarity", f"{pair.similarity:.1f} / 100", help=METHOD)
    else:
        st.info("Similarity unavailable: " + "; ".join(pair.reasons))
    common = set(pair.common_metrics)
    if len(common) >= 3:
        first = tuple(row for row in pair.reference.features if row.metric in common)
        second = tuple(row for row in pair.candidate.features if row.metric in common)
        names = tuple(
            f"{_name(data, key)} · {_club(data, key)}"
            for key in (pair.reference.player_team_id, pair.candidate.player_team_id)
        )
        st.plotly_chart(
            chart(first, second, names),
            theme=None,
            config={"displayModeBar": False},
            width="stretch",
        )
    else:
        st.info(
            "Radar unavailable: at least three common comparable features are needed."
        )
    st.caption(
        "One shared 0–100 percentile scale · Relative profiles, not player quality"
    )
    st.dataframe(
        explorer.pair_rows(pair),
        hide_index=True,
        width="stretch",
        column_config={
            key: st.column_config.NumberColumn(
                format="%.2f" if key in ("A", "B", "B − A") else "%.1f"
            )
            for key in ("A", "B", "A percentile", "B percentile", "B − A")
        },
    )
    st.caption("B − A uses unrounded raw values. Blank values are unavailable.")


def comparison_page(data, reference, chart):
    similar_view = st.session_state.get("explorer_view") == "similar"
    back, change = st.columns([3, 1])
    back.button("← Player profile", key="explorer_pair_back", on_click=_profile)
    change.button(
        "Search player B" if similar_view else "Change player B",
        key="explorer_pair_change",
        on_click=_pick,
    )
    st.subheader("Similar players" if similar_view else "Compare players")
    if "explorer_pair_mode" not in st.session_state:
        st.session_state["explorer_pair_mode"] = st.session_state.get(
            "explorer_pair_mode_saved", "Same position"
        )
    mode = st.radio(
        "Comparison population",
        ["Same position", "All players"],
        key="explorer_pair_mode",
        horizontal=True,
        help=METHOD,
    )
    st.session_state["explorer_pair_mode_saved"] = mode
    result = explorer.similar_profiles(data, reference, mode=mode)
    st.caption(
        f"{len(result.reference.peer_ids)} shared comparison rows · {len(result.feature_basis)} comparison metrics",
        help=METHOD,
    )
    second = st.session_state.get("explorer_pair_second")
    keys = {(row.player_id, row.team_id) for row in data.metrics.players}
    if second is not None and (
        second not in keys
        or second[0] == reference[0]
        or (
            mode == "Same position"
            and (
                explorer.position(data, reference[0]) == "Unknown"
                or explorer.position(data, second[0])
                != explorer.position(data, reference[0])
            )
        )
    ):
        st.session_state.pop("explorer_pair_second", None)
        st.session_state["explorer_pair_picking"] = True
        second = None
        st.caption("Player B selection updated for this population.")
    context = (
        st.session_state.get("explorer_source"),
        st.session_state.get("explorer_pair_epoch", 0),
    )
    if similar_view:
        st.caption(f"Reference: {_name(data, reference)} · {_club(data, reference)}")
        _suggestions(data, reference, result, context)
    elif st.session_state.get("explorer_pair_picking") or second is None:
        st.caption(f"Player A: {_name(data, reference)} · {_club(data, reference)}")
        if second is not None and st.button(
            "Keep current player B", key="explorer_pair_cancel"
        ):
            st.session_state["explorer_pair_picking"] = False
            st.rerun()
        _picker(data, reference, mode, result, context)
    else:
        _pair_view(
            data, explorer.compare_pair(data, reference, second, mode=mode), chart
        )
    with st.expander(f"Method and exclusions ({len(result.exclusions)})"):
        st.write(METHOD)
        st.caption(
            "Every candidate must supply all of A's comparable features (at least three). Incomplete or low-minute players can be inspected manually without a similarity score. Missing fields are never zero-filled."
        )
        if result.exclusions:
            st.dataframe(
                [
                    {
                        "Name": _name(data, key),
                        "Historical team": _club(data, key),
                        "Reason": "; ".join(reasons),
                    }
                    for key, reasons in result.exclusions
                ],
                hide_index=True,
                width="stretch",
            )
