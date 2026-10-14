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
