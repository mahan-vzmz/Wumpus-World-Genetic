from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from docs.build_artifacts import copy_assets, load_project_info, read_csv


def test_missing_project_info_has_clear_error(tmp_path: Path) -> None:
    missing = tmp_path / "missing_info.json"

    with pytest.raises(FileNotFoundError, match="Specified info file does not exist"):
        load_project_info(missing)


def test_placeholder_project_info_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "project_info.json"
    path.write_text(
        '{"report_mode": "academic", "student_name": "Your Name", "student_id": "123", '
        '"course_name": "AI", "instructor_name": "Prof", "university_name": "Uni", "submission_date": "2026-08-03"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="student_name"):
        load_project_info(path)


def test_invalid_report_mode_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "project_info.json"
    path.write_text(
        '{"report_mode": "publci", "project_title": "Wumpus", "author_name": "Author", "course_name": "AI"}',
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="report_mode"):
        load_project_info(path)


def test_valid_public_metadata_is_accepted(tmp_path: Path) -> None:
    path = tmp_path / "project_info.json"
    path.write_text(
        '{"report_mode": "public", "project_title": "Wumpus", "author_name": "Author", "course_name": "AI"}',
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


def test_retrain_summary_preserves_all_hyperparameters(tmp_path: Path) -> None:
    from wumpus_world.training.genetic_algorithm import (
        GenerationRecord,
        GeneticWeights,
        TrainingResult,
        save_training_artifacts,
    )
    result = TrainingResult(
        best_weights=GeneticWeights(),
        best_fitness=100.0,
        history=(GenerationRecord(0, 100.0, 90.0, 80.0),),
        seed=42,
        map_count=10,
        crossover_rate=0.75,
        patience=5,
    )
    weights_path = tmp_path / "weights.json"
    history_path = tmp_path / "history.csv"
    summary_path = tmp_path / "summary.json"

    save_training_artifacts(
        result,
        weights_path=weights_path,
        history_csv_path=history_path,
        summary_json_path=summary_path,
        provenance={"training_map_source": "test"}
    )

    import json
    summary = json.loads(summary_path.read_text())
    assert summary["crossover_rate"] == 0.75
    assert summary["patience"] == 5
    assert summary["training_map_source"] == "test"

    meta = json.loads(weights_path.read_text())["metadata"]
    assert meta["crossover_rate"] == 0.75
    assert meta["patience"] == 5


def test_asset_change_changes_report_fingerprint(tmp_path: Path) -> None:
    from docs.build_artifacts import report_fingerprint
    asset = tmp_path / "asset.png"
    asset.write_bytes(b"data1")
    fp1 = report_fingerprint("html", [asset], {"key": "value"})

    asset.write_bytes(b"data2")
    fp2 = report_fingerprint("html", [asset], {"key": "value"})
    assert fp1 != fp2


def test_pdf_hash_mismatch_forces_rebuild(tmp_path: Path) -> None:
    import json

    from docs.build_artifacts import build_report
    with patch("docs.build_artifacts.REPORT_DIR", tmp_path):
        manifest_path = tmp_path / "report_manifest.json"
        manifest_path.write_text(json.dumps({"source_fingerprint": "mock_fp", "pdf_sha256": "bad_hash"}))
        html_path = tmp_path / "final_report.html"
        html_path.write_text("<html></html>")
        pdf_path = tmp_path / "final_report.pdf"
        pdf_path.write_bytes(b"%PDF-1.4\n%%EOF\n")

        with patch("docs.build_artifacts.report_fingerprint", return_value="mock_fp"):
            with patch("docs.build_artifacts.preflight_pdf", return_value=1):
                from unittest.mock import MagicMock
                mock_weasyprint = MagicMock()
                with patch.dict("sys.modules", {"weasyprint": mock_weasyprint}):
                    try:
                        build_report({}, [], [])
                    except Exception:
                        pass
                    mock_weasyprint.HTML.assert_called()


def test_invalid_pdf_header_is_rejected(tmp_path: Path) -> None:
    from docs.build_artifacts import preflight_pdf
    pdf = tmp_path / "bad.pdf"
    pdf.write_bytes(b"NOT_A_PDF%%EOF")
    with pytest.raises(ValueError, match="PDF file header invalid"):
        preflight_pdf(pdf)


def test_pdf_without_eof_is_rejected(tmp_path: Path) -> None:
    from docs.build_artifacts import preflight_pdf
    pdf = tmp_path / "bad.pdf"
    pdf.write_bytes(b"%PDF-1.4\nMissing EOF marker")
    with pytest.raises(ValueError, match="PDF file trailer invalid"):
        preflight_pdf(pdf)


def test_academic_cover_contains_student_id_and_date(tmp_path: Path) -> None:
    path = tmp_path / "project_info.json"
    path.write_text(
        '{"report_mode": "academic", "student_name": "Name", "student_id": "12345", '
        '"course_name": "AI", "instructor_name": "Prof", "university_name": "Uni", "submission_date": "2026-08-03"}',
        encoding="utf-8",
    )
    from docs.build_artifacts import load_project_info
    info = load_project_info(path)
    assert info["student_id"] == "12345"
    assert info["submission_date"] == "2026-08-03"
