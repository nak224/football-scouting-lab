import subprocess
import sys
from pathlib import Path

import pytest

EXAMPLE = Path(__file__).resolve().parents[1] / "examples" / "replacement_ranking.py"


def invoke(data_dir, *args):
    return subprocess.run(
        [sys.executable, str(EXAMPLE), "--data-dir", str(data_dir), *args],
        cwd=data_dir,
        capture_output=True,
        text=True,
        check=False,
    )


def test_demo_does_not_fabricate_a_reference_for_synthetic_players(synthetic_data_dir):
    result = invoke(synthetic_data_dir)

    assert result.returncode == 2
    assert "reference (224677, 2447) is absent" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


def test_demo_reports_missing_events(synthetic_data_dir):
    (synthetic_data_dir / "events_Germany.json").unlink()

    result = invoke(synthetic_data_dir)

    assert result.returncode == 2
    assert "events_Germany.json" in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout


@pytest.mark.parametrize(
    "arguments,expected",
    [
        (["--style-priority", "1.1"], "style_priority"),
        (["--role", "team_fit"], "invalid choice"),
        (["--limit", "-1"], "shortlist limit"),
        (["--min-appearance-coverage", "1.1"], "coverage must be between 0 and 1"),
    ],
)
def test_demo_reports_invalid_configuration(synthetic_data_dir, arguments, expected):
    result = invoke(synthetic_data_dir, *arguments)

    assert result.returncode == 2
    assert expected in result.stderr
    assert "Traceback" not in result.stderr
    assert not result.stdout
