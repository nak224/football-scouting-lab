"""Actual Streamlit navigation and native selections using fictional records."""

import json

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")

from .test_explorer_app import APP, demo_app, select_row


def choose(app, *, column="Descriptive similarity", index=0):
    frame = next(
        frame for frame in app.tabs[0].dataframe if column in frame.value.columns
    )
    key = (
        int(frame.value.iloc[index]["Player ID"]),
        int(frame.value.iloc[index]["Team ID"]),
    )
    states = app._tree.get_widget_states()
    states.widgets.add(
        id=frame.proto.id,
        string_value=json.dumps(
            {"selection": {"rows": [index], "columns": [], "cells": []}}
        ),
    )
    app._run(states)
    assert not app.exception
    return key


def chart_spec(app):
    return json.loads(app.get("plotly_chart")[0].proto.spec)


def test_profile_actions_suggestions_shared_radar_and_roundtrip():
    app = demo_app()
    app.text_input(key="player_search").set_value("Avery").run()
    select_row(app, 0)
    reference = app.session_state["explorer_player"]
    app.button(key="explorer_similar_action").click().run()
    assert app.radio(key="explorer_pair_mode").value == "Same position"
    candidates = app.tabs[0].dataframe[0].value
    assert len(candidates) == 3  # four fictional source players, not a fabricated fifth
    assert (candidates["Player ID"] != reference[0]).all()
    assert candidates["Descriptive similarity"].is_monotonic_decreasing
    selected = choose(app)
    assert app.session_state["explorer_player"] == reference
    assert app.session_state["explorer_pair_second"] == selected
    spec = chart_spec(app)
    assert len(spec["data"]) == 2 and spec["layout"]["showlegend"]
    assert spec["data"][0]["line"]["color"] != spec["data"][1]["line"]["color"]
    assert spec["layout"]["polar"]["radialaxis"]["range"] == [0, 100]
    assert all(0 <= value <= 100 for trace in spec["data"] for value in trace["r"])
    assert all(trace["customdata"][0][1] == 4 for trace in spec["data"])
    table = next(
        frame.value for frame in app.tabs[0].dataframe if "B − A" in frame.value.columns
    )
    assert {"A", "B", "A percentile", "B percentile", "B − A", "Peers"} <= set(
        table.columns
    )
    app.button(key="explorer_pair_back").click().run()
    assert app.session_state["explorer_player"] == reference
    app.button(key="explorer_compare_action").click().run()
    assert app.session_state["explorer_pair_second"] == selected
    assert len(chart_spec(app)["data"]) == 2
    app.button(key="explorer_pair_back").click().run()
    app.button(key="explorer_back").click().run()
    assert app.text_input(key="player_search").value == "Avery"
    assert len(app.tabs[0].dataframe[0].value) == 1
    app.run()
    assert not any(button.key == "explorer_pair_back" for button in app.button)


def test_b_search_filters_and_change_preserve_a_and_its_percentiles():
    app = demo_app()
    select_row(app, 0)
    a = app.session_state["explorer_player"]
    app.button(key="explorer_compare_action").click().run()
    assert app.text_input(key="explorer_pair_query").label == "Player B name"
    app.text_input(key="explorer_pair_query").set_value("Casey").run()
    app.selectbox(key="explorer_pair_team").set_value(99002).run()
    app.selectbox(key="explorer_pair_position").set_value("Midfielder").run()
    b = choose(app, column="Name")
    first = chart_spec(app)["data"][0]["r"]
    app.button(key="explorer_pair_change").click().run()
    assert app.text_input(key="explorer_pair_query").value == "Casey"
    app.text_input(key="explorer_pair_query").set_value("Drew").run()
    app.selectbox(key="explorer_pair_team").set_value(None).run()
    new_b = choose(app, column="Name")
    assert new_b != b and app.session_state["explorer_player"] == a
    assert chart_spec(app)["data"][0]["r"] == first
    app.button(key="explorer_pair_change").click().run()
    app.text_input(key="explorer_pair_query").set_value("No such player").run()
    assert any("No players match" in info.value for info in app.tabs[0].info)
    app.button(key="explorer_pair_cancel").click().run()
    assert app.session_state["explorer_pair_second"] == new_b
    assert chart_spec(app)["data"][0]["r"] == first
    assert not app.exception


def test_unknown_position_defaults_to_all_players_and_source_switch_clears_pair(
    midfield_data_dir,
):
    from streamlit.testing.v1 import AppTest

    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_input(key="data_dir").set_value(str(midfield_data_dir))
    app.button(key="load_season").click().run()
    select_row(app, 0)
    app.button(key="explorer_similar_action").click().run()
    assert app.radio(key="explorer_pair_mode").value == "All players"
    choose(app)
    app.button(key="load_demo").click().run()
    assert not any(button.key == "explorer_pair_back" for button in app.button)
    assert set(app.tabs[0].dataframe[0].value["Position"]) == {"Midfielder"}
    assert "explorer_pair_second" not in app.session_state
    assert not app.exception


def test_missing_features_manual_comparison_remains_explicit_and_radar_has_no_zero_padding(
    midfield_data_dir,
):
    from streamlit.testing.v1 import AppTest

    path = midfield_data_dir / "events_Germany.json"
    events = json.loads(path.read_text())
    for event in events:
        if event["playerId"] == 20475:
            event["tags"] = []
    path.write_text(json.dumps(events))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_input(key="data_dir").set_value(str(midfield_data_dir))
    app.button(key="load_season").click().run()
    app.text_input(key="player_search").set_value("Thiago").run()
    select_row(app, 0)
    app.button(key="explorer_compare_action").click().run()
    app.text_input(key="explorer_pair_query").set_value("Vidal").run()
    choose(app, column="Name")
    assert any("Similarity unavailable" in info.value for info in app.tabs[0].info)
    assert any("Radar unavailable" in info.value for info in app.tabs[0].info)
    assert not app.get("plotly_chart")
    rows = app.tabs[0].dataframe[0].value
    assert rows["B"].isna().sum() == 2
    assert rows["B − A"].isna().sum() == 2
    assert not app.exception


def test_comparison_controls_reuse_season_calculation(monkeypatch):
    import streamlit as st

    from football_scouting_lab import ui_data

    st.cache_data.clear()
    calls = []
    original = ui_data.calculate_metrics

    def counted(*args):
        calls.append(1)
        return original(*args)

    monkeypatch.setattr(ui_data, "calculate_metrics", counted)
    app = demo_app()
    select_row(app, 0)
    app.button(key="explorer_compare_action").click().run()
    choose(app)
    app.radio(key="explorer_pair_mode").set_value("All players").run()
    app.button(key="explorer_pair_change").click().run()
    choose(app)
    app.button(key="explorer_pair_back").click().run()
    app.button(key="explorer_similar_action").click().run()
    assert len(calls) == 1
    assert not app.exception
