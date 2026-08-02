from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from docs.build_artifacts import copy_assets, load_project_info, read_csv


def test_missing_project_info_has_clear_error(tmp_path: Path) -> None:
    missing = tmp_path / "project_info.json"

    with pytest.raises(FileNotFoundError, match="project_info.example.json"):
        load_project_info(missing)


def test_placeholder_project_info_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "project_info.json"
    path.write_text(
        '{"student_name": "Your Name", "course_name": "AI", "instructor_name": "Prof", "university_name": "Uni"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="student_name"):
        load_project_info(path)


def test_valid_public_metadata_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "project_info.json"
    path.write_text(
        '{"report_mode": "public", "project_title": "Wumpus", "author_name": "Author"}',
        encoding="utf-8",
    )

    info = load_project_info(path)
    assert info["report_mode"] == "public"
    assert info["author_name"] == "Author"


def test_missing_summary_csv_fails_clearly(tmp_path: Path) -> None:
    missing = tmp_path / "summary_results.csv"
    with pytest.raises(FileNotFoundError):
        read_csv(missing)


def test_asset_copy_failure_is_not_ignored(tmp_path: Path) -> None:
    with patch("docs.build_artifacts.ASSETS", tmp_path / "readonly_assets"):
        (tmp_path / "readonly_assets").mkdir(parents=True, exist_ok=True)
        with patch.object(Path, "write_bytes", side_effect=OSError("Permission denied")):
            with pytest.raises(RuntimeError, match="Unable to update report asset"):
                copy_assets()
