import json
import subprocess
import sys


def invoke(data_dir):
    return subprocess.run(
        [sys.executable, "-m", "football_scouting_lab", "--data-dir", str(data_dir)],
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
