"""Complete no-download portfolio workflow; every demo result is fictional."""

from pathlib import Path

import pytest

streamlit = pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from football_scouting_lab import ui_data  # noqa: E402
from football_scouting_lab.fictional_data import BASELINE, CANDIDATE  # noqa: E402
from football_scouting_lab.team_fit import PROFILE_METRICS  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def demo_app():
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.button(key="load_demo").click().run()
    assert not app.exception
    return app


def test_complete_fictional_workflow_and_cached_controls(monkeypatch):
    # Other source-switching tests may already have warmed the AppTest cache.
    # Clear that cache too, rather than a separately imported bare-mode function.
    streamlit.cache_data.clear()
    calls = []
    original = ui_data.calculate_metrics

    def counted(metadata, events):
        calls.append(1)
        return original(metadata, events)

    monkeypatch.setattr(ui_data, "calculate_metrics", counted)
    app = demo_app()
    assert any(
        "FICTIONAL DEMO" in item.value
        and "NOT real Bundesliga statistics" in item.value
        for item in app.warning
    )
    assert len(app.tabs) == 3
    assert (
        len(app.warning) == 1
    )  # One clear source banner; routine sample notes are captions.
    before_role = (
        app.tabs[1]
        .dataframe[0]
        .value[["Player ID", "Role fit"]]
        .sort_values("Player ID")
    )
    assert len(app.tabs[0].dataframe[0].value) == 4
    app.text_input(key="player_search").set_value("Casey").run()
    assert len(app.tabs[0].dataframe[0].value) == 1
    app.selectbox(key="role").set_value("ball_winning_midfielder").run()
    app.number_input(
        key="role_weight_ball_winning_midfielder_interceptions_per90"
    ).set_value(100.0).run()
    app.number_input(key="style_weight_pass_attempts_per90").set_value(75.0).run()
    app.slider(key="style_priority").set_value(0.75).run()
    shortlist = app.tabs[1].dataframe[0].value
    assert len(shortlist) == 3
    assert (
        not shortlist[["Player ID", "Role fit"]]
        .sort_values("Player ID")
        .equals(before_role)
    )
    assert {
        "Rated minutes",
        "Coverage %",
        "Style similarity",
        "Role fit",
        "Combined score",
    } <= set(shortlist.columns)
    app.selectbox(key="explain_candidate").set_value(
        app.selectbox(key="explain_candidate").value
    ).run()
    assert any(
        "Reference value" in frame.value.columns for frame in app.tabs[1].dataframe
    )
    assert (
        tuple(app.selectbox(key=f"midfield_slot_{slot}").value for slot in range(3))
        == BASELINE
    )
    assert app.selectbox(key="midfield_candidate").value == CANDIDATE
    app.selectbox(key="midfield_replace_slot").set_value(0).run()
    app.selectbox(key="midfield_slot_0").set_value(CANDIDATE).run()
    assert app.selectbox(key="midfield_candidate").value == BASELINE[0]
    app.number_input(key="midfield_weight_interceptions_per90").set_value(100.0).run()
    assert any(
        "Coverage change" in frame.value.columns for frame in app.tabs[2].dataframe
    )
    assert len(calls) == 1
    assert not app.exception


def test_empty_and_invalid_demo_states_recover():
    app = demo_app()
    app.text_input(key="player_search").set_value("No such fictional player").run()
    assert any("No players match" in item.value for item in app.tabs[0].info)
    app.number_input(key="shortlist_length").set_value(0).run()
    assert any("shortlist is empty" in item.value for item in app.tabs[1].info)
    for metric in PROFILE_METRICS:
        app.number_input(key=f"midfield_weight_{metric}").set_value(0.0)
    app.run()
    assert any(
        "at least one profile weight" in item.value for item in app.tabs[2].warning
    )
    app.number_input(key="midfield_min_minutes").set_value(10000.0).run()
    assert any("simulator unavailable" in item.value for item in app.tabs[2].warning)
    app.button(key="load_demo").click().run()
    assert app.text_input(key="player_search").value == ""
    assert len(app.tabs[0].dataframe[0].value) == 4
    assert app.tabs[2].metric
    assert not app.exception


def test_local_and_fictional_sources_never_share_reviews_or_selections(
    midfield_data_dir,
):
    app = demo_app()
    app.text_input(key="player_search").set_value("Casey").run()
    app.text_input(key="data_dir").set_value(str(midfield_data_dir))
    app.button(key="load_season").click().run()
    assert not any("FICTIONAL DEMO" in item.value for item in app.warning)
    assert app.text_input(key="player_search").value == ""
    assert app.selectbox(key="midfield_slot_0").value == (3345, 2444)
    app.button(key="load_demo").click().run()
    assert any("FICTIONAL DEMO" in item.value for item in app.warning)
    assert app.selectbox(key="midfield_slot_0").value == BASELINE[0]
    assert not app.exception


def test_missing_local_files_hide_demo_results_until_demo_is_reloaded(tmp_path):
    app = demo_app()
    app.text_input(key="data_dir").set_value(str(tmp_path))
    app.button(key="load_season").click().run()
    assert "Missing data file" in app.error[0].value
    assert not app.tabs
    app.button(key="load_demo").click().run()
    assert len(app.tabs) == 3
    assert not app.error
    assert not app.exception
