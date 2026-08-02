from __future__ import annotations

import csv
import json
import re
import sys
from importlib.metadata import version
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    errors: list[str] = []

    # 1. Weights file checks
    weights_files = list(ROOT.glob("*weights*.json"))
    weights_names = [f.name for f in weights_files]
    if weights_names != ["best_weights.json"]:
        errors.append(f"Expected only best_weights.json in root; found {weights_names}")

    # 2. PDF report checks
    pdf_files = [f for f in ROOT.glob("**/*.pdf") if ".venv" not in f.parts and "build" not in f.parts]
    pdf_rel = [str(f.relative_to(ROOT)).replace("\\", "/") for f in pdf_files]
    if pdf_rel != ["docs/final_report/final_report.pdf"]:
        errors.append(f"Expected only docs/final_report/final_report.pdf; found {pdf_rel}")

    # 3. Version checks
    try:
        project_version = version("wumpus-world-genetic")
    except Exception:
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        match = re.search(r'version\s*=\s*"([^"]+)"', pyproject)
        project_version = match.group(1) if match else "8.1.0"

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    if project_version not in readme:
        errors.append(f"Version {project_version} not found in README.md")

    # 4. Obsolete references checks
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

    # 5. README links validation
    markdown_links = re.findall(r"\[.*?\]\((?!http)(.*?)\)", readme)
    for link in markdown_links:
        clean_link = link.split("#")[0]
        if not clean_link:
            continue
        target = ROOT / clean_link
        if not target.exists():
            errors.append(f"Broken link in README.md: {link}")

    # 6. Results metadata and benchmark row count verification
    test_manifest_path = ROOT / "maps" / "test" / "manifest.json"
    if test_manifest_path.exists():
        test_manifest = json.loads(test_manifest_path.read_text(encoding="utf-8"))
        num_maps = len(test_manifest)
        exp_csv = ROOT / "results" / "final" / "experiment_results.csv"
        if exp_csv.exists():
            with exp_csv.open(encoding="utf-8", newline="") as h:
                rows = list(csv.DictReader(h))
            expected_rows = num_maps * 3
            if len(rows) != expected_rows:
                errors.append(
                    f"Expected {expected_rows} experiment rows ({num_maps} maps * 3 agents); found {len(rows)}"
                )

    if errors:
        print("Repository consistency check failed:", file=sys.stderr)
        for err in errors:
            print(f" - {err}", file=sys.stderr)
        sys.exit(1)

    print("Repository consistency check passed cleanly.")


if __name__ == "__main__":
    main()
