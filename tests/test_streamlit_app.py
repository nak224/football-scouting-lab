"""Real Streamlit script interactions with explicitly synthetic local JSON files."""

import math
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from football_scouting_lab import ui_data  # noqa: E402
from football_scouting_lab.similarity import STYLE_METRICS  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"


def load_app(directory):
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    assert not app.exception
    app.text_input(key="data_dir").set_value(str(directory))
    app.button(key="load_season").click().run()
    assert not app.exception
    return app


def test_initial_and_missing_invalid_data(tmp_path):
    app = AppTest.from_file(str(APP)).run()
    assert not app.exception
    assert not app.dataframe
    app.text_input(key="data_dir").set_value(str(tmp_path))
    app.button(key="load_season").click().run()
    assert "Missing data file" in app.error[0].value
    assert not app.exception
    assert not app.dataframe


def test_explorer_search_filters_and_empty_results(ui_data_dir, ui_demo_reviews):
    app = load_app(ui_data_dir)
    assert "No reviewed reference" in app.info[-1].value  # default 600 minutes
    app.text_input(key="player_search").set_value("synthetic player a").run()
    frame = app.dataframe[0].value
    assert set(frame["Team ID"]) == {201, 202}
    assert len(frame) == 2
    app.selectbox[0].set_value(201).run()
    assert len(app.dataframe[0].value) == 1
    app.text_input(key="player_search").set_value("Nobody here").run()
    assert any("No players match" in row.value for row in app.info)
    assert not app.exception


def test_rank_controls_explanations_and_cache_reuse(
    ui_data_dir, ui_demo_reviews, monkeypatch
):
    calls = []
    original = ui_data.load_scouting_data

    def counted(directory):
        calls.append(directory)
        return original(directory)

    monkeypatch.setattr(ui_data, "load_scouting_data", counted)
    app = load_app(ui_data_dir)
    app.number_input(key="min_minutes").set_value(0.0).run()
    assert app.selectbox(key="reference").value == (101, 201)
    combined = app.dataframe[1].value.iloc[0]
    assert combined["Player ID"] == 104
    assert combined["Combined score"] == pytest.approx(
        0.5 * combined["Style similarity"] + 0.5 * combined["Role fit"]
    )
    assert len(app.dataframe[2].value) == 4  # feature differences
    assert len(app.dataframe[3].value) == 3  # role contributions
    app.slider(key="style_priority").set_value(1.0).run()
    style_only = app.dataframe[1].value.iloc[0]
    assert style_only["Combined score"] == style_only["Style similarity"]
    app.selectbox(key="role").set_value("ball_winning_midfielder").run()
    app.slider(key="style_priority").set_value(0.0).run()
    role_only = app.dataframe[1].value.iloc[0]
    assert role_only["Combined score"] == role_only["Role fit"]
    assert len(calls) == 1  # no reprocessing on ranking/filter changes
    app.number_input(key="shortlist_length").set_value(0).run()
    assert any("shortlist is empty" in row.value for row in app.info)
    for metric in STYLE_METRICS:
        app.number_input(key=f"style_weight_{metric}").set_value(0.0)
    app.run()
    assert any("at least one style weight" in row.value for row in app.warning)
    assert not app.exception
    assert len(calls) == 1
    app.checkbox(key="force_reload").check()
    app.button(key="load_season").click().run()
    assert len(calls) == 2  # explicitly requested source reload
    path = ui_data_dir / "teams.json"
    path.write_text(path.read_text() + "\n")
    app.run()
    assert len(calls) == 3  # cheap stat key invalidates cached metrics
    path.unlink()
    app.run()
    assert "Missing data file" in app.error[0].value
    assert not app.exception


def test_cache_returns_copies_and_explicit_reload(ui_data_dir, ui_demo_reviews):
    # Use the same decorated cache function as the application, without rendering it.
    import runpy

    namespace = runpy.run_path(str(APP), run_name="test_cache")
    cached = namespace["load_cached"]
    cached.clear()
    key = ui_data.dataset_key(str(ui_data_dir))
    first = cached(*key)
    first.player_names[101] = "Mutation in a caller"
    first.metrics.matches[0].period_minutes.clear()
    second = cached(*key)
    assert second.player_names[101] == "Synthetic Player A"
    assert second.metrics.matches[0].period_minutes == {"1H": 47, "2H": 49}
    cached.clear()


def test_invalid_json_and_reload_do_not_show_stale_results(
    ui_data_dir, ui_demo_reviews
):
    app = load_app(ui_data_dir)
    assert not app.error
    path = ui_data_dir / "events_Germany.json"
    path.write_text("not JSON")
    app.button(key="load_season").click().run()
    assert "cannot read JSON" in app.error[0].value
    assert not app.dataframe
    assert not app.exception


def test_role_weights_thresholds_and_review_filter(ui_data_dir, ui_demo_reviews):
    app = load_app(ui_data_dir)
    app.checkbox(key="cohort_only").check().run()
    assert set(app.dataframe[0].value["Position review"]) == {
        "Reviewed demo midfielder"
    }
    app.number_input(key="min_minutes").set_value(0.0).run()
    for metric in (
        "pass_attempts_per90",
        "pass_completion_pct",
        "accurate_passes_per90",
    ):
        app.number_input(key=f"role_weight_deep_lying_playmaker_{metric}").set_value(
            0.0
        )
    app.run()
    assert any("at least one metric weight" in row.value for row in app.warning)
    app.number_input(
        key="role_weight_deep_lying_playmaker_pass_attempts_per90"
    ).set_value(100.0).run()
    assert not app.exception
    app.number_input(key="min_minutes").set_value(10000.0).run()
    assert any("No reviewed reference" in row.value for row in app.info)
    assert not any(widget.key == "reference" for widget in app.selectbox)
    app.slider(key="min_coverage").set_value(100).run()
    app.number_input(key="min_minutes").set_value(0.0).run()
    assert app.selectbox(key="reference").value in ui_demo_reviews
    assert not app.exception


def test_missing_component_scores_show_exclusions(ui_data_dir, ui_demo_reviews):
    import json

    path = ui_data_dir / "events_Germany.json"
    events = json.loads(path.read_text())
    for event in events:
        if event["playerId"] == 104:
            event["tags"] = []  # explicitly ambiguous synthetic pass outcome
    path.write_text(json.dumps(events))
    app = load_app(ui_data_dir)
    app.number_input(key="min_minutes").set_value(0.0).run()
    assert not app.exception
    assert any("shortlist is empty" in row.value for row in app.info)
    exclusions = next(
        frame.value for frame in app.dataframe if "Reasons" in frame.value.columns
    )
    candidate = exclusions[
        exclusions["Player / historical team"].str.contains("104/202")
    ].iloc[0]
    assert candidate["Style similarity"] is None or math.isnan(
        candidate["Style similarity"]
    )
    assert "unavailable" in candidate["Reasons"]
