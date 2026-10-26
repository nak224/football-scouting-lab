"""Explorer native selection, navigation and comparisons with fictional fixtures."""

import json
import math
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
pytest.importorskip("plotly")
from streamlit.testing.v1 import AppTest  # noqa: E402

from football_scouting_lab import ui_data  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def demo_app():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button(key="load_demo").click().run()
    assert not app.exception
    return app


def select_row(app, index):
    # AppTest has no dataframe selection method. Send the same native widget
    # protobuf payload as the browser instead of writing read-only session state.
    frame = app.tabs[0].dataframe[0]
    states = app._tree.get_widget_states()
    states.widgets.add(
        id=frame.proto.id,
        string_value=json.dumps(
            {"selection": {"rows": [index], "columns": [], "cells": []}}
        ),
    )
    return app._run(states)


def test_native_selection_opens_profile_and_back_preserves_filters():
    app = demo_app()
    app.text_input(key="player_search").set_value("Casey").run()
    app.selectbox(key="explorer_position").set_value("Midfielder").run()
    assert len(app.tabs[0].dataframe[0].value) == 1
    select_row(app, 0)
    assert not app.exception
    assert any("FICTIONAL Casey North" == item.value for item in app.tabs[0].subheader)
    assert len(app.tabs[0].metric) == 4
    assert app.tabs[0].metric[0].value == "672"
    assert app.get("plotly_chart")
    chart = json.loads(app.get("plotly_chart")[0].proto.spec)
    assert chart["layout"]["polar"]["radialaxis"]["range"] == [0, 100]
    assert len(chart["data"][0]["r"]) == 5  # four real features, closed polygon
    assert all(0 <= value <= 100 for value in chart["data"][0]["r"])
    assert {"Metric", "Value", "Percentile", "Peers"} == set(
        app.tabs[0].dataframe[0].value.columns
    )
    app.button(key="explorer_back").click().run()
    assert app.text_input(key="player_search").value == "Casey"
    assert app.selectbox(key="explorer_position").value == "Midfielder"
    assert len(app.tabs[0].dataframe[0].value) == 1
    app.run()  # stale selection must not immediately reopen the profile
    assert not any(button.key == "explorer_back" for button in app.button)
    assert not app.exception


def test_four_filters_compact_results_and_empty_state(ui_data_dir):
    players_path = ui_data_dir / "players.json"
    players = json.loads(players_path.read_text())
    players[0]["role"] = {"name": "Midfielder"}
    players_path.write_text(json.dumps(players))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_input(key="data_dir").set_value(str(ui_data_dir))
    app.button(key="load_season").click().run()
    assert not app.exception
    assert [field.label for field in app.tabs[0].text_input] == ["Player name"]
    assert [field.label for field in app.tabs[0].selectbox] == [
        "League",
        "Historical team",
        "Position",
    ]
    assert app.tabs[0].selectbox[0].disabled
    frame = app.tabs[0].dataframe[0]
    assert "Position review" not in frame.value.columns
    config = json.loads(frame.proto.columns)
    assert config["Player ID"]["hidden"] and config["Team ID"]["hidden"]
    app.text_input(key="player_search").set_value("Synthetic Player A").run()
    assert len(app.tabs[0].dataframe[0].value) == 2  # historical transfer rows
    app.selectbox(key="team_filter").set_value(202).run()
    app.selectbox(key="explorer_position").set_value("Midfielder").run()
    assert len(app.tabs[0].dataframe[0].value) == 1
    select_row(app, 0)
    assert app.session_state["explorer_player"] == (101, 202)
    assert not app.get("plotly_chart")  # both season samples are below 600 minutes
    assert any("Radar unavailable" in info.value for info in app.tabs[0].info)
    app.button(key="explorer_back").click().run()
    app.selectbox(key="explorer_position").set_value("Unknown").run()
    assert any("No players match" in info.value for info in app.tabs[0].info)
    assert not app.exception


def test_unknown_position_toggle_and_tiny_population(midfield_data_dir):
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_input(key="data_dir").set_value(str(midfield_data_dir))
    app.button(key="load_season").click().run()
    select_row(app, 0)
    assert any("Position unknown" in info.value for info in app.tabs[0].info)
    assert not app.get("plotly_chart")
    app.radio(key="explorer_comparison").set_value("All players").run()
    assert app.get("plotly_chart")
    assert (app.tabs[0].dataframe[0].value["Peers"] == 4).all()
    assert not app.exception


def test_source_changes_clear_profiles_and_do_not_recalculate_on_controls(
    ui_data_dir, monkeypatch
):
    import streamlit as st

    st.cache_data.clear()
    calls = []
    original = ui_data.calculate_metrics

    def counted(*args):
        calls.append(1)
        return original(*args)

    monkeypatch.setattr(ui_data, "calculate_metrics", counted)
    app = demo_app()
    select_row(app, 0)
    app.radio(key="explorer_comparison").set_value("All players").run()
    app.button(key="explorer_back").click().run()
    app.selectbox(key="team_filter").set_value(99002).run()
    select_row(app, 0)
    assert len(calls) == 1
    app.text_input(key="data_dir").set_value(str(ui_data_dir))
    app.button(key="load_season").click().run()
    assert not any(button.key == "explorer_back" for button in app.button)
    assert set(app.tabs[0].dataframe[0].value["Position"]) == {"Unknown"}
    assert not app.get("plotly_chart")
    assert len(calls) == 2
    select_row(app, 0)
    path = ui_data_dir / "players.json"
    path.write_text(path.read_text() + "\n")
    app.run()
    assert not any(button.key == "explorer_back" for button in app.button)
    assert len(calls) == 3
    app.button(key="load_demo").click().run()
    assert set(app.tabs[0].dataframe[0].value["Position"]) == {"Midfielder"}
    assert app.text_input(key="player_search").value == ""
    assert not app.exception


def test_missing_measurements_do_not_draw_invented_radar_points(midfield_data_dir):
    path = midfield_data_dir / "events_Germany.json"
    events = json.loads(path.read_text())
    for event in events:
        if event["playerId"] == 20475:
            event["tags"] = []  # missing pass/defending outcomes, not zero successes
    path.write_text(json.dumps(events))
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_input(key="data_dir").set_value(str(midfield_data_dir))
    app.button(key="load_season").click().run()
    app.text_input(key="player_search").set_value("Vidal").run()
    select_row(app, 0)
    app.radio(key="explorer_comparison").set_value("All players").run()
    stats = app.tabs[0].dataframe[0].value.set_index("Metric")
    assert math.isnan(stats.loc["Pass completion %", "Value"])
    assert math.isnan(stats.loc["Defensive duels won /90", "Value"])
    assert not app.get("plotly_chart")
    assert any("Radar unavailable" in info.value for info in app.tabs[0].info)
    assert not app.exception


def test_review_edits_do_not_change_an_open_general_player_profile(
    midfield_data_dir, tmp_path
):
    reviews = tmp_path / "reviews.json"
    reviews.write_text("[]")
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_input(key="data_dir").set_value(str(midfield_data_dir))
    app.text_input(key="review_file").set_value(str(reviews))
    app.button(key="load_season").click().run()
    select_row(app, 0)
    app.radio(key="explorer_comparison").set_value("All players").run()
    selected = app.session_state["explorer_player"]
    original = app.tabs[0].dataframe[0].value.copy()
    reviews.write_text(
        json.dumps(
            [
                {
                    "player_id": selected[0],
                    "team_id": selected[1],
                    "status": "excluded",
                    "evidence": "synthetic:ui-isolation",
                    "note": "Fictional review for testing only.",
                }
            ]
        )
    )
    app.run()
    assert app.session_state["explorer_player"] == selected
    assert app.tabs[0].dataframe[0].value.equals(original)
    assert not app.exception
