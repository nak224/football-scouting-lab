"""Exercise the local example on synthetic JSON and fictional review decisions."""

import json
import runpy
from pathlib import Path

import pytest

from football_scouting_lab.roles import PositionReview

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "midfield_lineup.py"


@pytest.fixture
def example_main(ui_data_dir, monkeypatch):
    path = ui_data_dir / "events_Germany.json"
    events = json.loads(path.read_text())
    for player_id in (102, 103):
        events.append(
            {
                "id": len(events) + 1,
                "matchId": 1001,
                "teamId": 201,
                "playerId": player_id,
                "eventId": 8,
                "eventName": "Pass",
                "subEventId": 85,
                "subEventName": "Simple pass",
                "tags": [{"id": 1801}],
                "positions": [],
                "matchPeriod": "2H",
                "eventSec": 1200,
            }
        )
    path.write_text(json.dumps(events))
    main = runpy.run_path(str(EXAMPLE))["main"]
    baseline = ((101, 201), (102, 201), (103, 201))
    candidate = (104, 202)
    review = PositionReview("included", "synthetic:test", "Fictional midfielder")
    monkeypatch.setitem(main.__globals__, "BASELINE_LINEUP", baseline)
    monkeypatch.setitem(main.__globals__, "CANDIDATE_ID", candidate)
    monkeypatch.setitem(
        main.__globals__,
        "DEMO_REVIEWS",
        {key: review for key in (*baseline, candidate)},
    )
    return main, ui_data_dir


def test_example_prints_hypothetical_context_features_and_samples(example_main, capsys):
    main, directory = example_main
    assert main(["--data-dir", str(directory), "--min-rated-minutes", "0"]) == 0
    output = capsys.readouterr().out
    assert "HYPOTHETICAL 4-3-3" in output
    assert "not an actual historical starting XI" in output
    assert "not assumed to have played together" in output
    assert "Replace slot 2: (103, 201) with (104, 202)" in output
    assert "coverage=" in output
    assert "raw_before=" in output
    assert "Weighted coverage change:" in output
    assert "Unknown-player events: 4" in output


def test_example_does_not_silently_drop_ineligible_cohort_rows(example_main, capsys):
    main, directory = example_main
    with pytest.raises(SystemExit) as error:
        main(["--data-dir", str(directory)])  # defaults require 600 minutes
    assert error.value.code == 2
    assert "fails thresholds" in capsys.readouterr().err


def test_example_missing_local_files(tmp_path, capsys):
    main = runpy.run_path(str(EXAMPLE))["main"]
    with pytest.raises(SystemExit) as error:
        main(["--data-dir", str(tmp_path)])
    assert error.value.code == 2
    assert "cannot read JSON" in capsys.readouterr().err


def test_example_requires_complete_demo_presence(example_main, capsys, monkeypatch):
    main, directory = example_main
    reviews = dict(main.__globals__["DEMO_REVIEWS"])
    reviews[(999, 201)] = PositionReview(
        "included", "synthetic:test", "Fictional missing player"
    )
    monkeypatch.setitem(main.__globals__, "DEMO_REVIEWS", reviews)
    with pytest.raises(SystemExit) as error:
        main(["--data-dir", str(directory), "--min-rated-minutes", "0"])
    assert error.value.code == 2
    assert "not fully present" in capsys.readouterr().err
