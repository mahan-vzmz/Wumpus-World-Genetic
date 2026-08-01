import sys
from pathlib import Path

import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))
from docs.build_artifacts import load_project_info


def test_missing_project_info_has_clear_error(tmp_path: Path) -> None:
    missing = tmp_path / "project_info.json"

    with pytest.raises(FileNotFoundError, match="project_info.example.json"):
        load_project_info(missing)
