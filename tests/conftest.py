from pathlib import Path
from shutil import copytree

import pytest


@pytest.fixture
def synthetic_data_dir(tmp_path):
    """Copy hand-authored fictional records; never use external data in tests."""
    source = Path(__file__).parent / "fixtures" / "wyscout"
    return copytree(source, tmp_path / "wyscout")
