"""External cohorts in the real-file UI flow, using ONLY synthetic source files."""

import json
from pathlib import Path

import pytest

pytest.importorskip("streamlit")
from streamlit.testing.v1 import AppTest  # noqa: E402

from football_scouting_lab import ui_data  # noqa: E402
from football_scouting_lab.fictional_data import BASELINE, write_fictional_data  # noqa: E402

APP = Path(__file__).resolve().parents[1] / "streamlit_app.py"
PAIRS = ((3345, 2444), (20475, 2444), (224677, 2447), (289711, 2975))


def write_reviews(path, pairs=PAIRS, excluded=(), evidence="synthetic:test-review"):
    path.write_text(
        json.dumps(
            [
                {
                    "player_id": player,
                    "team_id": team,
                    "status": "excluded" if (player, team) in excluded else "included",
                    "evidence": evidence,
                    "note": "Invented fixture decision, no real football evidence.",
                }
                for player, team in pairs
            ]
        )
    )
    return path


def load_app(directory, reviews):
    app = AppTest.from_file(str(APP), default_timeout=30).run()
    app.text_input(key="data_dir").set_value(str(directory))
    app.text_input(key="review_file").set_value(str(reviews))
    app.button(key="load_season").click().run()
    assert not app.exception
    return app


def evidence_table(app):
    return next(
        frame.value for frame in app.dataframe if "Decision" in frame.value.columns
    )


def test_reviews_refresh_references_candidates_evidence_without_recalculating(
    midfield_data_dir, tmp_path, monkeypatch
):
    calls = []
    original = ui_data.calculate_metrics

    def counted(*args):
        calls.append(1)
        return original(*args)

    monkeypatch.setattr(ui_data, "calculate_metrics", counted)
    path = write_reviews(tmp_path / "reviews.json")
    app = load_app(midfield_data_dir, path)
    assert app.selectbox(key="reference").value == (224677, 2447)
    assert len(app.tabs[1].dataframe[0].value) == 3
    assert len(evidence_table(app)) == 4
    assert set(evidence_table(app)["Evidence"]) == {"synthetic:test-review"}
    assert any("4 included · 0 excluded" in item.value for item in app.caption)
    # Discovery uses broad source positions, independently of recruitment reviews.
    assert "Position review" not in app.tabs[0].dataframe[0].value.columns
    discovery = app.tabs[0].dataframe[0].value.copy()
    app.slider(key="style_priority").set_value(0.75).run()
    # Same file path, revised decisions and evidence. No Load season required.
    write_reviews(path, excluded=((224677, 2447),), evidence="synthetic:revised")
    app.run()
    assert app.selectbox(key="reference").value != (224677, 2447)
    assert not any(
        "224677/2447" in option for option in app.selectbox(key="reference").options
    )
    assert app.slider(key="style_priority").value == 0.75
    assert len(app.tabs[1].dataframe[0].value) == 2
    assert any("at least four distinct" in item.value for item in app.tabs[2].warning)
    assert set(evidence_table(app)["Evidence"]) == {"synthetic:revised"}
    assert app.tabs[0].dataframe[0].value.equals(discovery)
    exclusions = next(
        frame.value
        for frame in app.tabs[2].dataframe
        if "Exclusion reason" in frame.value.columns
    )
    assert "position review: excluded" in str(exclusions)
    write_reviews(path)
    app.run()
    assert app.selectbox(key="midfield_candidate").value == (20475, 2444)
    app.selectbox(key="midfield_slot_0").set_value((20475, 2444)).run()
    app.number_input(key="midfield_weight_pass_attempts_per90").set_value(50.0).run()
    # Applying another path and clearing the config also reuse the season cache.
    second = write_reviews(tmp_path / "other.json", excluded=((289711, 2975),))
    app.text_input(key="review_file").set_value(str(second))
    app.button(key="load_season").click().run()
    assert any("at least four distinct" in item.value for item in app.tabs[2].warning)
    app.text_input(key="review_file").set_value("")
    app.button(key="load_season").click().run()
    assert app.selectbox(key="midfield_candidate").value == (20475, 2444)
    assert any("only four reviewed" in item.value for item in app.info)
    assert not app.error and not app.exception
    assert len(calls) == 1


def test_invalid_and_empty_reviews_hide_stale_results_and_recover(
    midfield_data_dir, tmp_path
):
    path = write_reviews(tmp_path / "reviews.json", pairs=())
    app = load_app(midfield_data_dir, path)
    assert any("No reviewed reference" in item.value for item in app.tabs[1].info)
    assert any("review set is empty" in item.value for item in app.info)
    assert not any(widget.key == "midfield_candidate" for widget in app.selectbox)
    assert not app.error
    for invalid, message in (
        ("not JSON", "cannot read review JSON"),
        (json.dumps([{"player_id": 1}]), "exactly these fields"),
    ):
        path.write_text(invalid)
        app.run()
        assert message in app.error[0].value
        assert not app.tabs and not app.dataframe and not app.exception
    write_reviews(path)
    app.run()
    assert len(app.tabs) == 3 and app.tabs[2].metric
    path.unlink()
    app.run()
    assert "cannot read review JSON" in app.error[0].value
    assert not app.dataframe and not app.exception


def test_custom_reviews_do_not_leak_into_demo_or_cached_default(
    midfield_data_dir, tmp_path
):
    path = write_reviews(tmp_path / "reviews.json", excluded=(PAIRS[2],))
    app = load_app(midfield_data_dir, path)
    assert len(app.tabs[1].dataframe[0].value) == 2
    # A now-missing real review file must be ignored throughout fictional mode.
    path.unlink()
    app.button(key="load_demo").click().run()
    assert app.selectbox(key="midfield_slot_0").value == BASELINE[0]
    assert len(app.tabs[1].dataframe[0].value) == 3
    assert not app.error and not app.exception
    assert any("FICTIONAL DEMO" in item.value for item in app.warning)
    write_reviews(path, excluded=(PAIRS[2],))
    app.button(key="load_season").click().run()
    assert len(app.tabs[1].dataframe[0].value) == 2
    assert not any("FICTIONAL DEMO" in item.value for item in app.warning)
    app.text_input(key="review_file").set_value("")
    app.button(key="load_season").click().run()
    assert len(app.tabs[1].dataframe[0].value) == 3
    assert not app.exception


def test_transfer_reviews_keep_historical_team_decisions_separate(
    ui_data_dir, tmp_path
):
    pairs = ((101, 201), (101, 202), (104, 202))
    path = write_reviews(tmp_path / "reviews.json", pairs, excluded=((101, 202),))
    app = load_app(ui_data_dir, path)
    app.number_input(key="min_minutes").set_value(0.0).run()
    assert app.selectbox(key="reference").value == (101, 201)
    assert len(app.tabs[1].dataframe[0].value) == 1
    assert app.tabs[1].dataframe[0].value.iloc[0]["Player ID"] == 104
    rows = evidence_table(app)
    transfer = rows[rows["Player ID"] == 101]
    assert set(transfer["Team ID"]) == {201, 202}
    assert set(transfer["Decision"]) == {"included", "excluded"}
    assert not app.exception


def test_local_files_marked_fictional_reject_external_reviews(tmp_path):
    root = write_fictional_data(tmp_path / "fictional")
    path = write_reviews(tmp_path / "reviews.json", pairs=())
    app = load_app(root, path)
    assert "cannot be applied to FICTIONAL" in app.error[0].value
    assert not app.tabs and not app.exception
    app.text_input(key="review_file").set_value("")
    app.button(key="load_season").click().run()
    assert any("FICTIONAL DEMO" in item.value for item in app.warning)
    assert app.selectbox(key="midfield_slot_0").value == BASELINE[0]
    assert not app.error and not app.exception


def test_external_cohort_need_not_contain_any_default_demo_ids(
    midfield_data_dir, tmp_path
):
    # Remap this synthetic fixture to other invented player IDs, retaining clubs.
    mapping = {player: player + 6_000_000 for player, _ in PAIRS}
    for name in ("players.json", "matches_Germany.json", "events_Germany.json"):
        path = midfield_data_dir / name
        records = json.loads(path.read_text())
        if name == "players.json":
            for player in records:
                player["wyId"] = mapping[player["wyId"]]
        elif name == "matches_Germany.json":
            for match in records:
                for team in match["teamsData"].values():
                    formation = team["formation"]
                    for player in (*formation["lineup"], *formation["bench"]):
                        player["playerId"] = mapping[player["playerId"]]
        else:
            for event in records:
                event["playerId"] = mapping.get(event["playerId"], event["playerId"])
        path.write_text(json.dumps(records))
    pairs = tuple((mapping[player], team) for player, team in PAIRS)
    path = write_reviews(tmp_path / "reviews.json", pairs)
    app = load_app(midfield_data_dir, path)
    assert app.selectbox(key="reference").value in pairs
    assert app.selectbox(key="midfield_candidate").value in pairs
    assert len(app.tabs[1].dataframe[0].value) == 3
    assert app.tabs[2].metric
    assert set(evidence_table(app)["Player ID"]) == set(mapping.values())
    assert not app.error and not app.exception


def test_missing_global_metadata_does_not_invalidate_a_known_unused_bench_pair(
    ui_data_dir, tmp_path
):
    path = ui_data_dir / "players.json"
    players = json.loads(path.read_text())
    path.write_text(json.dumps([row for row in players if row["wyId"] != 109]))
    reviews = write_reviews(tmp_path / "reviews.json", pairs=((109, 201),))
    app = load_app(ui_data_dir, reviews)
    assert not app.error and not app.exception
    row = evidence_table(app).iloc[0]
    assert row["Player ID"] == 109
    assert row["Player metadata"] == "Missing from players.json"
    assert row["Metric sample"] == "No player/team metric sample"
    assert any("No reviewed reference" in item.value for item in app.tabs[1].info)
    assert not app.tabs[2].metric
    assert not any(widget.key == "reference" for widget in app.selectbox)
