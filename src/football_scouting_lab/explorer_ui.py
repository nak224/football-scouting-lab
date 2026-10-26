"""Local discovery/profile views; scoring stays in the existing analytics APIs."""

import hashlib

import plotly.graph_objects as go
import streamlit as st

from . import explorer
from .comparison_ui import comparison_page, open_comparison
from .ui_data import POSITION_GROUPS

COMPARISON_HELP = (
    "Peers have at least 600 rated minutes. Missing values are excluded per metric "
    "(minimum two peers). Midrank percentiles; constant groups = 50. "
    "Transfers stay separate. Small groups are unstable."
)
RADAR_LABELS = (
    "Passes /90",
    "Pass<br>completion",
    "Interceptions<br>/90",
    "Defensive<br>duels won /90",
)
STAT_LABELS = {
    **explorer.LABELS,
    "successful_defensive_duels_per90": "Defensive duels won /90",
}


def radar_figure(features, other=None, names=None):
    labels = [RADAR_LABELS[explorer.FEATURES.index(row.metric)] for row in features]
    values = [row.percentile for row in features]
    raw = [[row.value, row.peer_count] for row in features]
    figure = go.Figure(
        go.Scatterpolar(
            r=[*values, values[0]],
            theta=[*labels, labels[0]],
            customdata=[*raw, raw[0]],
            mode="lines+markers",
            fill="toself",
            line={"color": "#2563eb", "width": 2.5},
            marker={"size": 7, "color": "#2563eb"},
            fillcolor="rgba(37,99,235,0.15)",
            hovertemplate="%{theta}<br>Value: %{customdata[0]:.2f}<br>Percentile: %{r:.1f}<br>Peers: %{customdata[1]}<extra></extra>",
        )
    )
    figure.update_layout(
        height=300,
        margin={"l": 70, "r": 70, "t": 35, "b": 35},
        paper_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font={"family": "Arial, sans-serif", "color": "#475569", "size": 12},
        polar={
            "bgcolor": "rgba(0,0,0,0)",
            "radialaxis": {
                "range": [0, 100],
                "tickvals": [0, 25, 50, 75, 100],
                "angle": 45,
                "tickfont": {"size": 10, "color": "#64748b"},
                "gridcolor": "#e2e8f0",
                "linecolor": "#e2e8f0",
                "ticks": "",
            },
            "angularaxis": {
                "rotation": 90,
                "direction": "clockwise",
                "gridcolor": "#e2e8f0",
                "linecolor": "#e2e8f0",
            },
        },
    )
    if other is not None:
        second_values = [row.percentile for row in other]
        second_raw = [[row.value, row.peer_count] for row in other]
        figure.data[0].name = names[0]
        figure.add_trace(
            go.Scatterpolar(
                name=names[1],
                r=[*second_values, second_values[0]],
                theta=[*labels, labels[0]],
                customdata=[*second_raw, second_raw[0]],
                mode="lines+markers",
                fill="toself",
                line={"color": "#d97706", "width": 2.5},
                marker={"size": 7, "color": "#d97706"},
                fillcolor="rgba(217,119,6,0.12)",
                hovertemplate=figure.data[0].hovertemplate,
            )
        )
        figure.update_layout(
            height=350,
            showlegend=True,
            legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": -0.16},
            margin={"l": 70, "r": 70, "t": 30, "b": 65},
        )
    return figure


def _back_to_list():
    st.session_state.pop("explorer_player", None)
    st.session_state["explorer_view"] = "profile"
    st.session_state["explorer_epoch"] = st.session_state.get("explorer_epoch", 0) + 1


def player_profile(data, key):
    player = next(
        row for row in data.metrics.players if (row.player_id, row.team_id) == key
    )
    back, compare, similar = st.columns([3, 1, 1])
    back.button("← Player list", key="explorer_back", on_click=_back_to_list)
    compare.button(
        "Compare player",
        key="explorer_compare_action",
        on_click=open_comparison,
        args=(data, key, "compare"),
    )
    similar.button(
        "Similar players",
        key="explorer_similar_action",
        on_click=open_comparison,
        args=(data, key, "similar"),
    )
    st.subheader(data.player_names.get(key[0], f"Player {key[0]}"))
    group = explorer.position(data, key[0])
    team = data.team_names.get(key[1], f"Team {key[1]}")
    st.caption(
        f"{team} · {group} · {explorer.SEASON}"
        + (" · Fictional demo" if data.fictional else "")
    )
    values = explorer.measurements(player)
    appearances = sum(row.appearance_recorded for row in player.matches)
    rated = sum(row.appearance_recorded and row.rate_eligible for row in player.matches)
    minutes = player.rated_minutes
    cards = st.columns(4)
    cards[0].metric(
        "Rated minutes",
        f"{minutes:,.0f}" if minutes and minutes > 0 else "—",
        help="Estimated minutes in the rated sample; period ends approximate the final whistle.",
    )
    cards[1].metric(
        "Rated appearances",
        f"{rated} / {appearances}",
        help="Rated recorded appearances / all recorded appearances. Missing timing can bias the sample.",
    )
    for column, metric, label, suffix in (
        (cards[2], "pass_attempts_per90", "Pass attempts /90", ""),
        (cards[3], "pass_completion_pct", "Pass completion", "%"),
    ):
        value = values[metric]
        column.metric(label, f"{value:.1f}{suffix}" if value is not None else "—")
    if "explorer_comparison" not in st.session_state:
        st.session_state["explorer_comparison"] = st.session_state.get(
            "explorer_profile_mode", "Same position"
        )
    mode = st.radio(
        "Compare with",
        ["Same position", "All players"],
        horizontal=True,
        key="explorer_comparison",
        help=COMPARISON_HELP,
    )
    st.session_state["explorer_profile_mode"] = mode
    result = explorer.compare_player(data, key, mode=mode)
    st.caption(
        f"{len(result.peer_ids)} comparable player/team rows", help=COMPARISON_HELP
    )
    left, right = st.columns([1.1, 1], gap="large")
    with left:
        st.markdown("**Statistical profile**")
        features = explorer.radar_features(result)
        if features:
            st.plotly_chart(
                radar_figure(features),
                theme=None,
                config={"displayModeBar": False},
                width="stretch",
            )
            st.caption("0–100 percentiles · Relative profile, not player quality")
        elif group == "Unknown" and mode == "Same position":
            st.info("Position unknown. Choose All players to compare.")
        else:
            st.info("Radar unavailable: at least three comparable metrics are needed.")
    with right:
        st.markdown("**Season statistics**")
        st.dataframe(
            [
                {
                    "Metric": STAT_LABELS[row.metric],
                    "Value": row.value,
                    "Percentile": row.percentile,
                    "Peers": row.peer_count,
                }
                for row in result.features
            ],
            hide_index=True,
            width="stretch",
            column_config={
                "Value": st.column_config.NumberColumn(format="%.1f"),
                "Percentile": st.column_config.ProgressColumn(
                    min_value=0, max_value=100, format="%.1f", help=COMPARISON_HELP
                ),
                "Peers": st.column_config.NumberColumn(
                    help="Available comparison rows for this metric. Fewer than two leaves the percentile unavailable."
                ),
            },
        )
        st.caption("Blank values are unavailable.")
        if not minutes or minutes < explorer.MIN_COMPARISON_MINUTES:
            st.caption(
                "Limited playing-time sample",
                help="This player is below the 600-minute comparison threshold. Available statistics are shown, but this row does not enter the peer population.",
            )


def player_explorer(data, source_key):
    if st.session_state.get("explorer_source") != source_key:
        for key in list(st.session_state):
            if key.startswith("explorer_"):
                st.session_state.pop(key)
        st.session_state["player_search"] = ""
        st.session_state["team_filter"] = None
        st.session_state["explorer_source"] = source_key
    selected = st.session_state.get("explorer_player")
    keys = {(row.player_id, row.team_id) for row in data.metrics.players}
    if selected in keys:
        if st.session_state.get("explorer_view") in ("compare", "similar"):
            comparison_page(data, selected, radar_figure)
        else:
            player_profile(data, selected)
        return
    st.session_state.pop("explorer_player", None)
    st.subheader("Discover players")
    saved = st.session_state.get("explorer_filters", {})
    for key, fallback in (
        ("player_search", ""),
        ("team_filter", None),
        ("explorer_position", None),
    ):
        if key not in st.session_state:
            st.session_state[key] = saved.get(key, fallback)
    search, league, team_column, position_column = st.columns([1.5, 1.2, 1.3, 1])
    query = search.text_input(
        "Player name", key="player_search", placeholder="Search players…"
    )
    league.selectbox(
        "League",
        [explorer.LEAGUE],
        disabled=True,
        help="Only Bundesliga 2017/18 is supported. The demo uses fictional records.",
    )
    teams = sorted(
        {row.team_id for row in data.metrics.players},
        key=lambda key: (data.team_names.get(key, ""), key),
    )
    if st.session_state["team_filter"] not in (None, *teams):
        st.session_state["team_filter"] = None
    team = team_column.selectbox(
        "Historical team",
        [None, *teams],
        key="team_filter",
        placeholder="All teams",
        format_func=lambda key: (
            "All teams" if key is None else data.team_names.get(key, f"Team {key}")
        ),
    )
    present = {explorer.position(data, row.player_id) for row in data.metrics.players}
    positions = [
        None,
        *(group for group in (*POSITION_GROUPS, "Unknown") if group in present),
    ]
    if st.session_state["explorer_position"] not in positions:
        st.session_state["explorer_position"] = None
    group = position_column.selectbox(
        "Position",
        positions,
        key="explorer_position",
        placeholder="All positions",
        format_func=lambda value: value or "All positions",
        help="Original broad player role, not a match-specific tactical position.",
    )
    st.session_state["explorer_filters"] = {
        "player_search": query,
        "team_filter": team,
        "explorer_position": group,
    }
    rows = explorer.discovery_rows(
        data, query=query, team_id=team, player_position=group
    )
    if not rows:
        st.info("No players match these filters.")
        return
    st.caption(
        f"{len(rows)} result{'s' if len(rows) != 1 else ''} · Select a row to open a profile"
    )
    context = (
        source_key,
        query.strip().casefold(),
        team,
        group,
        st.session_state.get("explorer_epoch", 0),
    )
    token = hashlib.sha256(repr(context).encode()).hexdigest()[:20]
    event = st.dataframe(
        rows,
        hide_index=True,
        width="stretch",
        height=min(465, 40 + 36 * len(rows)),
        key=f"explorer_results_{token}",
        on_select="rerun",
        selection_mode="single-row",
        column_order=[
            "Name",
            "Historical team",
            "Position",
            "Rated minutes",
            "Pass attempts /90",
            "Pass completion %",
            "Interceptions /90",
        ],
        column_config={
            "Player ID": None,
            "Team ID": None,
            "Position": st.column_config.TextColumn(
                help="Original Wyscout role.name. Missing or unrecognized roles stay Unknown."
            ),
            "Rated minutes": st.column_config.NumberColumn(format="%.0f"),
            **{
                label: st.column_config.NumberColumn(format="%.1f")
                for label in explorer.LABELS.values()
            },
            "Pass attempts /90": st.column_config.NumberColumn(
                "Passes /90", format="%.1f"
            ),
            "Pass completion %": st.column_config.NumberColumn("Pass %", format="%.1f"),
        },
    )
    key = explorer.selected_player(rows, event.selection.rows)
    if key is not None:
        st.session_state["explorer_player"] = key
        st.session_state["explorer_view"] = "profile"
        st.rerun()
