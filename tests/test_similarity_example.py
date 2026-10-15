import subprocess
import sys
from pathlib import Path

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "player_similarity.py"


def invoke(data_dir, *args):
    return subprocess.run(
        [sys.executable, str(EXAMPLE), "--data-dir", str(data_dir), *args],
        cwd=data_dir,
        capture_output=True,
        text=True,
        check=False,
    )


def test_demo_never_invents_a_reviewed_reference_for_synthetic_players(
    synthetic_data_dir,
):
    result = invoke(synthetic_data_dir)

    assert result.returncode == 2
    assert "reference (224677, 2447) is absent" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


def test_demo_rejects_an_unreviewed_reference(synthetic_data_dir):
    result = invoke(
        synthetic_data_dir, "--reference-player", "101", "--reference-team", "201"
    )

    assert result.returncode == 2
    assert "position review: unverified" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


def test_demo_reports_missing_events(synthetic_data_dir):
    (synthetic_data_dir / "events_Germany.json").unlink()

    result = invoke(synthetic_data_dir)

    assert result.returncode == 2
    assert "events_Germany.json" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


def test_demo_rejects_invalid_eligibility_threshold(synthetic_data_dir):
    result = invoke(synthetic_data_dir, "--min-appearance-coverage", "1.1")

    assert result.returncode == 2
    assert "coverage must be between 0 and 1" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout
