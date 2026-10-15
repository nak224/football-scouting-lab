import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "midfield_roles.py"


def invoke(data_dir, *args):
    return subprocess.run(
        [sys.executable, str(EXAMPLE), "--data-dir", str(data_dir), *args],
        cwd=data_dir,
        capture_output=True,
        text=True,
        check=False,
    )


def test_example_keeps_synthetic_players_unverified(synthetic_data_dir):
    result = invoke(synthetic_data_dir)

    assert result.returncode == 0
    assert "Loaded: 2 matches, 5 events" in result.stdout
    assert "Demo reviews present: 0 / 4" in result.stdout
    assert "deep_lying_playmaker: reference size 0" in result.stdout
    assert "ball_winning_midfielder: reference size 0" in result.stdout
    assert "position review: unverified" in result.stdout
    assert "score=" not in result.stdout
    assert result.stderr == ""


def test_example_reports_missing_data(synthetic_data_dir):
    (synthetic_data_dir / "events_Germany.json").unlink()

    result = invoke(synthetic_data_dir)

    assert result.returncode == 2
    assert "events_Germany.json" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


def test_example_rejects_invalid_thresholds(synthetic_data_dir):
    result = invoke(synthetic_data_dir, "--min-appearance-coverage", "1.1")

    assert result.returncode == 2
    assert "coverage must be between 0 and 1" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout
