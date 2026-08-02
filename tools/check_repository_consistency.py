from __future__ import annotations

import csv
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_WEIGHTS = ROOT / "best_weights.json"
PACKAGED_WEIGHTS = ROOT / "src" / "wumpus_world" / "data" / "best_weights.json"
RUN_METADATA_PATH = ROOT / "results" / "final" / "run_metadata.json"
SUMMARY_CSV_PATH = ROOT / "results" / "final" / "summary_results.csv"
EXPERIMENT_CSV_PATH = ROOT / "results" / "final" / "experiment_results.csv"
FINAL_REPORT_HTML = ROOT / "docs" / "final_report" / "final_report.html"
FINAL_REPORT_PDF = ROOT / "docs" / "final_report" / "final_report.pdf"


def sha256_file(path: Path) -> str:
    if not path.exists():
        return ""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def get_pyproject_version() -> str:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', pyproject)
    return match.group(1) if match else "8.1.0"


def check_weight_integrity(errors: list[str]) -> None:
    if not ROOT_WEIGHTS.exists():
        errors.append(f"Missing root weights file: {ROOT_WEIGHTS}")
        return
    if not PACKAGED_WEIGHTS.exists():
        errors.append(f"Missing packaged weights file: {PACKAGED_WEIGHTS}")
        return

    root_hash = sha256_file(ROOT_WEIGHTS)
    packaged_hash = sha256_file(PACKAGED_WEIGHTS)

    if root_hash != packaged_hash:
        errors.append(
            f"Weight hash mismatch between root ({root_hash[:12]}) and package ({packaged_hash[:12]}). "
            "Run python tools/sync_packaged_weights.py"
        )

    if RUN_METADATA_PATH.exists():
        try:
            meta = json.loads(RUN_METADATA_PATH.read_text(encoding="utf-8"))
            recorded_hash = meta.get("weights_sha256", "")
            if recorded_hash != root_hash:
                errors.append(
                    f"Recorded weights_sha256 ({recorded_hash[:12]}) in run_metadata.json "
                    f"does not match best_weights.json ({root_hash[:12]})"
                )
        except Exception as exc:
            errors.append(f"Failed to read run_metadata.json: {exc}")


def check_run_metadata(errors: list[str]) -> None:
    if not RUN_METADATA_PATH.exists():
        errors.append(f"Missing run metadata file: {RUN_METADATA_PATH}")
        return

    try:
        data = json.loads(RUN_METADATA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Invalid JSON in run_metadata.json: {exc}")
        return

    source_commit = data.get("source_commit", "").strip()
    if not source_commit or source_commit == "unknown":
        errors.append("run_metadata.json contains invalid or unknown source_commit")

    meta_version = data.get("project_version", "")
    expected_version = get_pyproject_version()
    if meta_version != expected_version:
        errors.append(
            f"project_version in run_metadata.json ({meta_version}) does not match pyproject.toml ({expected_version})"
        )


def check_report_metadata(errors: list[str]) -> None:
    info_path = ROOT / "project_info.public.json"
    if not info_path.exists():
        info_path = ROOT / "project_info.json"

    if not info_path.exists():
        errors.append("Neither project_info.public.json nor project_info.json exists")
        return

    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Invalid JSON in {info_path.name}: {exc}")
        return

    mode = info.get("report_mode", "").lower()
    if mode not in {"public", "academic"}:
        errors.append(f"report_mode in {info_path.name} must be 'public' or 'academic'; got '{mode}'")

    placeholders = {"Your Name", "Your Student ID", "Instructor Name", "University Name", "YYYY-MM-DD", "Project Title"}
    invalid = {k: v for k, v in info.items() if v in placeholders}
    if invalid:
        errors.append(f"Placeholder values in {info_path.name}: {', '.join(sorted(invalid))}")


def check_result_consistency(errors: list[str]) -> None:
    test_manifest_path = ROOT / "maps" / "test" / "manifest.json"
    if not test_manifest_path.exists():
        errors.append(f"Missing test manifest: {test_manifest_path}")
        return

    test_manifest = json.loads(test_manifest_path.read_text(encoding="utf-8"))
    num_maps = len(test_manifest)

    if not EXPERIMENT_CSV_PATH.exists():
        errors.append(f"Missing experiment CSV: {EXPERIMENT_CSV_PATH}")
    else:
        with EXPERIMENT_CSV_PATH.open(encoding="utf-8", newline="") as h:
            rows = list(csv.DictReader(h))
        expected_rows = num_maps * 3
        if len(rows) != expected_rows:
            errors.append(f"Expected {expected_rows} experiment rows ({num_maps} maps * 3 agents); found {len(rows)}")

    if SUMMARY_CSV_PATH.exists() and FINAL_REPORT_HTML.exists():
        with SUMMARY_CSV_PATH.open(encoding="utf-8", newline="") as h:
            summary_rows = list(csv.DictReader(h))
        html_text = FINAL_REPORT_HTML.read_text(encoding="utf-8")
        for row in summary_rows:
            rate_str = f"{row['success_rate']}"
            if rate_str not in html_text:
                errors.append(
                    f"Success rate {rate_str}% for agent '{row['agent']}' not found in {FINAL_REPORT_HTML.name}"
                )


def check_obsolete_references(errors: list[str]) -> None:
    stale_patterns = [
        (r"\bmain\.py\b", "main.py"),
        (r"\bdemo_all\.py\b", "demo_all.py"),
        (r"\bFILE_MANIFEST\.sha256\b", "FILE_MANIFEST.sha256"),
        (r"WUMPUS WORLD VERSION 8\b(?! \.)", "WUMPUS WORLD VERSION 8 without minor version"),
        (r"best_weights_backup\.json", "best_weights_backup.json"),
    ]

    files_to_check = [
        ROOT / "README.md",
        ROOT / "README_FA.md",
        ROOT / "docs" / "02-architecture.md",
        ROOT / "docs" / "final_report" / "final_report.html",
        ROOT / "experiment.py",
        ROOT / "verify_delivery.py",
    ]

    for file_path in files_to_check:
        if not file_path.exists():
            continue
        text = file_path.read_text(encoding="utf-8")
        for pattern, label in stale_patterns:
            if re.search(pattern, text):
                errors.append(f"Obsolete reference '{label}' found in {file_path.relative_to(ROOT)}")


def check_canonical_artifacts(errors: list[str]) -> None:
    weights_files = list(ROOT.glob("*weights*.json"))
    weights_names = [f.name for f in weights_files]
    if weights_names != ["best_weights.json"]:
        errors.append(f"Expected only best_weights.json in root; found {weights_names}")

    pdf_files = [
        f for f in ROOT.glob("**/*.pdf") if ".venv" not in f.parts and "build" not in f.parts and "dist" not in f.parts
    ]
    pdf_rel = [str(f.relative_to(ROOT)).replace("\\", "/") for f in pdf_files]
    if pdf_rel != ["docs/final_report/final_report.pdf"]:
        errors.append(f"Expected only docs/final_report/final_report.pdf; found {pdf_rel}")


def main() -> None:
    errors: list[str] = []

    check_canonical_artifacts(errors)
    check_weight_integrity(errors)
    check_run_metadata(errors)
    check_report_metadata(errors)
    check_result_consistency(errors)
    check_obsolete_references(errors)

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    markdown_links = re.findall(r"\[.*?\]\((?!http)(.*?)\)", readme)
    for link in markdown_links:
        clean_link = link.split("#")[0]
        if not clean_link:
            continue
        target = ROOT / clean_link
        if not target.exists():
            errors.append(f"Broken link in README.md: {link}")

    if errors:
        print("Repository consistency check failed:", file=sys.stderr)
        for err in errors:
            print(f" - {err}", file=sys.stderr)
        sys.exit(1)

    print("Repository consistency check passed cleanly.")


if __name__ == "__main__":
    main()
