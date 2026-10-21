"""Third-tab interactions with entirely fictional local files matching default IDs."""

import json
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from football_scouting_lab import team_fit, ui_data  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
BASELINE = ((3345, 2444), (224677, 2447), (289711, 2975))
CANDIDATE = (20475, 2444)


def load_app(directory):
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_input(key="data_dir").set_value(str(directory))
    app.button[0].click().run()
    assert not app.exception
    assert not app.error
    return app


def frame_with(app, column):
    return next(
        frame.value for frame in app.tabs[2].dataframe if column in frame.value.columns
    )


def signed_change(app):
    return next(
        metric.value
        for metric in app.tabs[2].metric
        if metric.label == "Signed weighted coverage change"
    )


def baseline(app):
    return tuple(app.selectbox(key=f"midfield_slot_{slot}").value for slot in range(3))


def test_defaults_lineups_explanations_and_direct_backend_call(
    midfield_data_dir, monkeypatch
):
    calls = []
    original = team_fit.compare_midfield

    def compared(cohort, lineup, slot, candidate, **kwargs):
        result = original(cohort, lineup, slot, candidate, **kwargs)
        calls.append(result)
        return result

    monkeypatch.setattr(team_fit, "compare_midfield", compared)
    app = load_app(midfield_data_dir)
    assert [tab.label for tab in app.tabs] == [
        "Player explorer",
        "Replacement finder",
        "Midfield simulator",
    ]
    assert baseline(app) == BASELINE
    assert app.selectbox(key="midfield_replace_slot").value == 2
    assert app.selectbox(key="midfield_candidate").value == CANDIDATE
    result = calls[-1]
    assert result.baseline_lineup == BASELINE
    assert result.updated_lineup == (*BASELINE[:2], CANDIDATE)
    assert len(result.comparison_cohort) == 4
    assert signed_change(app) == "+25.00 points"
    assert (
        frame_with(app, "Coverage change")["Weighted contribution (points)"].sum()
        == result.weighted_coverage_change
    )
    lineups = [
        frame.value
        for frame in app.tabs[2].dataframe
        if "Change" in frame.value.columns
    ]
    assert lineups[0].iloc[2]["Change"] == "Removed"
    assert "Fictional Keita" in lineups[0].iloc[2]["Player / historical team"]
    assert lineups[1].iloc[2]["Change"] == "Added"
    assert "Fictional Vidal" in lineups[1].iloc[2]["Player / historical team"]
    assert any(
        "not an observed historical XI" in item.value for item in app.tabs[2].markdown
    )
    assert any("tiny comparison cohort" in item.value for item in app.tabs[2].warning)
    samples = frame_with(app, "Source warnings")
    assert len(samples) == 4
    assert (samples["Appearance coverage %"] == 100).all()
    assert samples["Source warnings"].str.contains("last observed event").all()


def test_swaps_and_candidate_repair_keep_fixed_feature_ranges(midfield_data_dir):
    app = load_app(midfield_data_dir)
    initial = frame_with(app, "Minimum").copy()
    app.selectbox(key="midfield_replace_slot").set_value(0).run()
    assert signed_change(app) == "+12.50 points"
    assert frame_with(app, "Minimum").equals(initial)
    # Select the previous candidate into the baseline; the remaining player becomes candidate.
    app.selectbox(key="midfield_slot_0").set_value(CANDIDATE).run()
    assert app.selectbox(key="midfield_candidate").value == BASELINE[0]
    assert frame_with(app, "Minimum").equals(initial)
    assert not app.exception
    # Choosing another occupied slot triggers repair rather than a duplicated underlying player.
    app.selectbox(key="midfield_slot_0").set_value(BASELINE[1]).run()
    assert len({key[0] for key in baseline(app)}) == 3
    assert app.selectbox(key="midfield_candidate").value[0] not in {
        key[0] for key in baseline(app)
    }
    assert any("selection updated" in item.value for item in app.tabs[2].caption)
    assert not app.exception


def test_weights_use_backend_contributions_without_season_recalculation(
    midfield_data_dir, monkeypatch
):
    calculations = []
    original = ui_data.calculate_metrics

    def counted(metadata, events):
        calculations.append(1)
        return original(metadata, events)

    monkeypatch.setattr(ui_data, "calculate_metrics", counted)
    app = load_app(midfield_data_dir)
    ranges = frame_with(app, "Minimum")[["Feature", "Minimum", "Maximum"]].copy()
    for metric in team_fit.PROFILE_METRICS:
        app.number_input(key=f"midfield_weight_{metric}").set_value(
            100.0 if metric == "interceptions_per90" else 0.0
        )
    app.run()
    assert signed_change(app) == "+50.00 points"
    assert frame_with(app, "Minimum")[["Feature", "Minimum", "Maximum"]].equals(ranges)
    app.selectbox(key="midfield_replace_slot").set_value(0).run()
    app.selectbox(key="midfield_slot_0").set_value(CANDIDATE).run()
    app.slider(key="midfield_min_coverage").set_value(100).run()
    app.number_input(key="midfield_min_minutes").set_value(650.0).run()
    assert not app.exception
    assert len(calculations) == 1


def test_all_zero_weights_and_input_bounds_recover_gracefully(midfield_data_dir):
    app = load_app(midfield_data_dir)
    for metric in team_fit.PROFILE_METRICS:
        app.number_input(key=f"midfield_weight_{metric}").set_value(0.0)
    app.run()
    assert any(
        "at least one profile weight" in warning.value
        for warning in app.tabs[2].warning
    )
    assert not app.tabs[2].metric
    app.number_input(key="midfield_weight_pass_attempts_per90").set_value(-5.0).run()
    # Streamlit rejects an out-of-bounds widget value and restores its default.
    assert app.number_input(key="midfield_weight_pass_attempts_per90").value >= 0
    assert not app.exception
    app.number_input(key="midfield_weight_pass_attempts_per90").set_value(100.0).run()
    assert signed_change(app) == "+0.00 points"
    assert not app.exception


def test_incomplete_candidate_is_excluded_before_cohort_comparison(
    midfield_data_dir, monkeypatch
):
    path = midfield_data_dir / "events_Germany.json"
    events = json.loads(path.read_text())
    next(
        event
        for event in events
        if event["playerId"] == CANDIDATE[0] and event["eventId"] == 8
    )["tags"] = []
    path.write_text(json.dumps(events))
    calls = []
    monkeypatch.setattr(
        team_fit, "compare_midfield", lambda *args, **kwargs: calls.append(args)
    )
    app = load_app(midfield_data_dir)
    assert any(
        "at least four distinct reviewed players" in warning.value
        for warning in app.tabs[2].warning
    )
    assert any(
        "pass_completion_pct" in reason
        for reason in frame_with(app, "Exclusion reason")["Exclusion reason"]
    )
    assert not any(widget.key == "midfield_candidate" for widget in app.selectbox)
    assert not calls
    assert not app.exception


def test_threshold_empty_state_and_recovery(midfield_data_dir):
    app = load_app(midfield_data_dir)
    app.number_input(key="midfield_min_minutes").set_value(10000.0).run()
    assert not app.tabs[2].metric
    assert not any(widget.key == "midfield_slot_0" for widget in app.selectbox)
    assert (
        frame_with(app, "Exclusion reason")["Exclusion reason"]
        .str.contains("below minimum rated minutes")
        .all()
    )
    app.number_input(key="midfield_min_minutes").set_value(600.0).run()
    assert baseline(app) == BASELINE
    assert signed_change(app) == "+25.00 points"
    assert not app.exception


def test_changed_source_resets_selections_then_reports_missing_demo_and_files(
    midfield_data_dir,
):
    app = load_app(midfield_data_dir)
    app.selectbox(key="midfield_slot_0").set_value(CANDIDATE).run()
    players_path = midfield_data_dir / "players.json"
    players = json.loads(players_path.read_text())
    players[0]["shortName"] = "Changed fictional name"
    players_path.write_text(json.dumps(players))
    app.run()
    assert baseline(app) == BASELINE
    assert any(
        "selections have been reset" in item.value for item in app.tabs[2].caption
    )
    matches_path = midfield_data_dir / "matches_Germany.json"
    matches = [
        match
        for match in json.loads(matches_path.read_text())
        if "2975" not in match["teamsData"]
    ]
    matches_path.write_text(json.dumps(matches))
    ids = {match["wyId"] for match in matches}
    events_path = midfield_data_dir / "events_Germany.json"
    events = [
        event
        for event in json.loads(events_path.read_text())
        if event["matchId"] in ids
    ]
    events_path.write_text(json.dumps(events))
    app.run()
    assert not app.exception
    assert not app.tabs[2].metric
    assert any(
        "absent from local metrics" in reason
        for reason in frame_with(app, "Exclusion reason")["Exclusion reason"]
    )
    assert not any(widget.key == "midfield_candidate" for widget in app.selectbox)
    events_path.unlink()
    app.run()
    assert "Missing data file" in app.error[0].value
    assert not app.tabs
    assert not app.exception


def test_constant_feature_warning_and_zero_change(midfield_data_dir):
    path = midfield_data_dir / "events_Germany.json"
    events = json.loads(path.read_text())
    for event in events:
        event["tags"] = [tag for tag in event["tags"] if tag["id"] != 1401]
    path.write_text(json.dumps(events))
    app = load_app(midfield_data_dir)
    assert any(
        "constant feature interceptions_per90" in warning.value
        for warning in app.tabs[2].warning
    )
    row = (
        frame_with(app, "Coverage change").set_index("Feature").loc["Interceptions /90"]
    )
    assert row["Before coverage"] == row["After coverage"] == 0.5
    assert row["Coverage change"] == row["Weighted contribution (points)"] == 0
    assert not app.exception
