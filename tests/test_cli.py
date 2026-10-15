import csv
import json
import subprocess
import sys


def invoke(data_dir, *extra_args):
    return subprocess.run(
        [
            sys.executable,
            "-m",
            "football_scouting_lab",
            "--data-dir",
            str(data_dir),
            *extra_args,
        ],
        cwd=data_dir,
        capture_output=True,
        text=True,
        check=False,
    )


def test_cli_summarizes_match_references_not_global_metadata(synthetic_data_dir):
    result = invoke(synthetic_data_dir)

    assert result.returncode == 0
    assert result.stdout == (
        "Wyscout Bundesliga 2017/18\n"
        "Matches: 2\n"
        "Teams: 2\n"
        "Referenced players: 7 (includes unused bench)\n"
        "Players recorded as appearing: 6\n"
    )
    assert result.stderr == ""


def test_cli_reports_missing_files_without_a_traceback(synthetic_data_dir):
    (synthetic_data_dir / "matches_Germany.json").unlink()

    result = invoke(synthetic_data_dir)

    assert result.returncode == 2
    assert "error:" in result.stderr
    assert "matches_Germany.json" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


def test_cli_warns_about_missing_player_metadata(synthetic_data_dir):
    path = synthetic_data_dir / "players.json"
    records = json.loads(path.read_text())
    path.write_text(json.dumps(records[1:]))

    result = invoke(synthetic_data_dir)

    assert result.returncode == 0
    assert "Referenced players: 7" in result.stdout
    assert result.stderr == "warning: player IDs missing from players.json: 101\n"


def test_metadata_only_ignores_an_invalid_event_file(synthetic_data_dir):
    (synthetic_data_dir / "events_Germany.json").write_text("not JSON")

    result = invoke(synthetic_data_dir)

    assert result.returncode == 0
    assert "Matches: 2" in result.stdout
    assert "Events:" not in result.stdout
    assert not result.stderr


def test_optional_event_summary_reports_discrepancies(synthetic_data_dir):
    result = invoke(synthetic_data_dir, "--events")

    assert result.returncode == 0
    assert "Referenced players: 7 (includes unused bench)" in result.stdout
    assert "Players recorded as appearing: 6" in result.stdout
    assert "Events: 5" in result.stdout
    assert "Matches with events: 2 / 2" in result.stdout
    assert "Event types: 1=1, 7=1, 8=2, 10=1" in result.stdout
    assert "Match periods: 1H=3, 2H=2" in result.stdout
    assert result.stderr == (
        "warning: 1 events have unknown playerId 0\n"
        "warning: 1 events reference missing player metadata\n"
        "warning: 2 events reference players outside the match-team squad\n"
    )


def test_optional_events_require_the_event_file(synthetic_data_dir):
    (synthetic_data_dir / "events_Germany.json").unlink()

    result = invoke(synthetic_data_dir, "--events")

    assert result.returncode == 2
    assert "events_Germany.json" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


def test_invalid_events_fail_before_printing_a_partial_summary(synthetic_data_dir):
    path = synthetic_data_dir / "events_Germany.json"
    events = json.loads(path.read_text())
    events[0]["matchId"] = 9999
    path.write_text(json.dumps(events))

    result = invoke(synthetic_data_dir, "--events")

    assert result.returncode == 2
    assert "matchId 9999 missing from loaded matches" in result.stderr
    assert not result.stdout


def test_cli_reports_outside_coordinates_as_data_quality_warnings(synthetic_data_dir):
    path = synthetic_data_dir / "events_Germany.json"
    events = json.loads(path.read_text())
    events[0]["positions"][0]["x"] = 101
    path.write_text(json.dumps(events))

    result = invoke(synthetic_data_dir, "--events")

    assert result.returncode == 0
    assert "warning: 1 events have positions outside [0, 100]" in result.stderr


def test_metrics_csv_implies_events_and_keeps_unknown_values_empty(synthetic_data_dir):
    output = synthetic_data_dir.parent / "metrics.csv"

    result = invoke(synthetic_data_dir, "--metrics-csv", str(output))

    assert result.returncode == 0
    assert "Events: 5" in result.stdout
    assert "Usable match durations: 0 / 2" in result.stdout
    assert "Excluded match 1001" in result.stdout
    assert "1 unknown-player events excluded from player metrics" in result.stdout
    with output.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    row = next(r for r in rows if (r["player_id"], r["team_id"]) == ("101", "201"))
    assert row["observed_pass_attempts"] == "1"
    assert row["observed_accurate_passes"] == "1"
    assert row["observed_match_ids"] == "1001"
    assert row["unknown_minutes_matches"] == "1"
    assert row["rated_matches"] == "0"
    assert row["rated_minutes"] == ""
    assert row["rated_pass_attempts"] == ""
    assert row["pass_attempts_per90"] == ""
    assert "completeness unknown" in row["warnings"]


def test_metrics_csv_exports_actual_covered_rates(synthetic_data_dir):
    path = synthetic_data_dir / "matches_Germany.json"
    matches = json.loads(path.read_text())
    for match in matches:
        match["duration"] = "Regular"
        for team in match["teamsData"].values():
            for p in team["formation"]["lineup"] + team["formation"]["bench"]:
                p["redCards"] = "0"
    path.write_text(json.dumps(matches))
    path = synthetic_data_dir / "events_Germany.json"
    events = json.loads(path.read_text())
    events[0]["eventSec"] = 47 * 60
    events[2].update(matchPeriod="2H", eventSec=49 * 60)
    path.write_text(json.dumps(events))
    output = synthetic_data_dir.parent / "metrics.csv"

    result = invoke(synthetic_data_dir, "--events", "--metrics-csv", str(output))

    assert result.returncode == 0
    with output.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    row = next(r for r in rows if (r["player_id"], r["team_id"]) == ("101", "201"))
    assert row["rated_match_ids"] == "1001"
    assert row["rated_matches"] == "1"
    assert float(row["rated_minutes"]) == 96
    assert float(row["rated_pass_completion_pct"]) == 100
    assert float(row["pass_attempts_per90"]) == 90 / 96


def test_metrics_export_requires_events_before_creating_output(synthetic_data_dir):
    (synthetic_data_dir / "events_Germany.json").unlink()
    output = synthetic_data_dir.parent / "metrics.csv"

    result = invoke(synthetic_data_dir, "--metrics-csv", str(output))

    assert result.returncode == 2
    assert "events_Germany.json" in result.stderr
    assert not result.stdout
    assert not output.exists()


def test_metrics_export_never_overwrites_source_or_existing_output(synthetic_data_dir):
    output = synthetic_data_dir / "events_Germany.json"
    original = output.read_bytes()

    result = invoke(synthetic_data_dir, "--metrics-csv", str(output))

    assert result.returncode == 2
    assert "cannot write metrics CSV" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout
    assert output.read_bytes() == original


def test_metrics_export_reports_invalid_destination(synthetic_data_dir):
    result = invoke(
        synthetic_data_dir,
        "--metrics-csv",
        str(synthetic_data_dir / "missing" / "m.csv"),
    )

    assert result.returncode == 2
    assert "cannot write metrics CSV" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout
