from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROOT_WEIGHTS = ROOT / "best_weights.json"
PACKAGED_WEIGHTS = ROOT / "src" / "wumpus_world" / "data" / "best_weights.json"
TRAINING_SUMMARY_PATH = ROOT / "results" / "genetic_training_summary.json"
RUN_METADATA_PATH = ROOT / "results" / "final" / "run_metadata.json"
SUMMARY_CSV_PATH = ROOT / "results" / "final" / "summary_results.csv"
DIFFICULTY_CSV_PATH = ROOT / "results" / "final" / "difficulty_results.csv"
EXPERIMENT_CSV_PATH = ROOT / "results" / "final" / "experiment_results.csv"
FINAL_REPORT_HTML = ROOT / "docs" / "final_report" / "final_report.html"
CHANGELOG_PATH = ROOT / "CHANGELOG.md"


def canonical_json_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        canonical = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(canonical).hexdigest()
    except Exception:
        raw_bytes = path.read_bytes()
        normalized_bytes = raw_bytes.replace(b"\r\n", b"\n")
        return hashlib.sha256(normalized_bytes).hexdigest()


def get_pyproject_version() -> str:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'version\s*=\s*"([^"]+)"', pyproject)
    return match.group(1) if match else "8.1.1"


def get_changelog_latest_version() -> str:
    if not CHANGELOG_PATH.exists():
        return ""
    text = CHANGELOG_PATH.read_text(encoding="utf-8")
    match = re.search(r"##\s+Version\s+([0-9]+\.[0-9]+\.[0-9]+)", text)
    return match.group(1) if match else ""


def check_git_tracking(errors: list[str]) -> None:
    public_info = ROOT / "project_info.public.json"
    if not public_info.exists():
        errors.append("Missing project_info.public.json in repository")
    else:
        proc = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "project_info.public.json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            errors.append("project_info.public.json must be tracked in Git")

    proc_academic = subprocess.run(
        ["git", "ls-files", "project_info.json"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc_academic.returncode == 0 and proc_academic.stdout.strip():
        errors.append("project_info.json must NOT be tracked in Git (run `git rm --cached project_info.json`)")


def check_weight_integrity(errors: list[str]) -> None:
    if not ROOT_WEIGHTS.exists():
        errors.append(f"Missing root weights file: {ROOT_WEIGHTS}")
        return
    if not PACKAGED_WEIGHTS.exists():
        errors.append(f"Missing packaged weights file: {PACKAGED_WEIGHTS}")
        return

    root_hash = canonical_json_sha256(ROOT_WEIGHTS)
    packaged_hash = canonical_json_sha256(PACKAGED_WEIGHTS)

    if root_hash != packaged_hash:
        errors.append(
            f"Weight hash mismatch between root ({root_hash[:12]}) and package ({packaged_hash[:12]}). "
            "Run python tools/sync_packaged_weights.py"
        )

    if RUN_METADATA_PATH.exists():
        try:
            meta = json.loads(RUN_METADATA_PATH.read_text(encoding="utf-8"))
            recorded_hash = meta.get("weights_canonical_sha256", "")
            if recorded_hash != root_hash:
                errors.append(
                    f"Recorded weights_canonical_sha256 ({recorded_hash[:12]}) in run_metadata.json "
                    f"does not match best_weights.json ({root_hash[:12]})"
                )
        except Exception as exc:
            errors.append(f"Failed to read run_metadata.json: {exc}")


def check_training_metadata_consistency(errors: list[str]) -> None:
    if not TRAINING_SUMMARY_PATH.exists():
        errors.append(f"Missing training summary file: {TRAINING_SUMMARY_PATH}")
        return
    if not RUN_METADATA_PATH.exists():
        errors.append(f"Missing run metadata file: {RUN_METADATA_PATH}")
        return

    try:
        training = json.loads(TRAINING_SUMMARY_PATH.read_text(encoding="utf-8"))
        run_meta = json.loads(RUN_METADATA_PATH.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Failed to parse training summary or run metadata JSON: {exc}")
        return

    field_pairs = {
        "seed": "training_seed",
        "map_count": "training_maps",
        "population": "population",
        "requested_generations": "requested_generations",
        "generations_run": "generations_run",
        "mutation_rate": "mutation_rate",
        "mutation_sigma": "mutation_sigma",
        "crossover_rate": "crossover_rate",
        "patience": "patience",
        "elite_count": "elite_count",
        "tournament_size": "tournament_size",
        "training_max_steps": "training_max_steps",
        "training_map_source": "training_map_source",
        "training_map_seed": "training_map_seed",
        "training_suite_sha256": "training_suite_sha256",
    }

    for training_key, run_key in field_pairs.items():
        val_t = training.get(training_key)
        val_r = run_meta.get(run_key)
        if val_t != val_r:
            errors.append(
                f"Training metadata mismatch for {training_key}/{run_key}: training={val_t!r}, run_metadata={val_r!r}"
            )

    if abs(float(training.get("best_fitness", 0)) - float(run_meta.get("best_fitness", 0))) > 1e-4:
        errors.append(
            f"best_fitness mismatch: training={training.get('best_fitness')}, run_metadata={run_meta.get('best_fitness')}"
        )

    if ROOT_WEIGHTS.exists():
        try:
            root_weights_json = json.loads(ROOT_WEIGHTS.read_text(encoding="utf-8"))

            root_meta = root_weights_json.get("metadata", {})
            for key, val in root_meta.items():
                # For map count, the key in training summary might be map_count but it's matched
                if key in training:
                    t_val = training[key]
                    if isinstance(val, float) or isinstance(t_val, float):
                        if abs(float(val) - float(t_val)) > 1e-4:
                            errors.append(f"Weight metadata mismatch for '{key}': weight={val} != summary={t_val}")
                    elif val != t_val:
                        errors.append(f"Weight metadata mismatch for '{key}': weight={val} != summary={t_val}")

            root_genes = root_weights_json.get("genes", {})
            summary_genes = training.get("best_weights", {})
            if set(summary_genes.keys()) != set(root_genes.keys()):
                errors.append(
                    f"Weight genes mismatch: summary genes {set(summary_genes.keys())} != best_weights genes {set(root_genes.keys())}"
                )
            for key, val in summary_genes.items():
                if abs(float(val) - float(root_genes.get(key, 0))) > 1e-4:
                    errors.append(
                        f"Weight gene '{key}' mismatch between training summary ({val}) and best_weights.json ({root_genes.get(key)})"
                    )
        except Exception as exc:
            errors.append(f"Failed to verify best_weights genes: {exc}")


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
    if not re.fullmatch(r"[0-9a-f]{40}", source_commit):
        errors.append(f"source_commit must be a full 40-character Git SHA; got '{source_commit}'")
    else:
        proc = subprocess.run(
            ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            shallow_proc = subprocess.run(
                ["git", "rev-parse", "--is-shallow-repository"],
                cwd=ROOT,
                capture_output=True,
                text=True,
                check=False,
            )
            if shallow_proc.returncode == 0 and shallow_proc.stdout.strip() == "true":
                subprocess.run(
                    ["git", "fetch", "--depth=1", "origin", source_commit],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
                proc = subprocess.run(
                    ["git", "cat-file", "-e", f"{source_commit}^{{commit}}"],
                    cwd=ROOT,
                    capture_output=True,
                    text=True,
                    check=False,
                )
            if proc.returncode != 0:
                errors.append(f"source_commit '{source_commit}' does not exist in local Git object database")

    meta_version = data.get("project_version", "")
    expected_version = get_pyproject_version()
    if meta_version != expected_version:
        errors.append(
            f"project_version in run_metadata.json ({meta_version}) does not match pyproject.toml ({expected_version})"
        )

    changelog_version = get_changelog_latest_version()
    if changelog_version != expected_version:
        errors.append(
            f"Latest version in CHANGELOG.md ({changelog_version}) does not match pyproject.toml ({expected_version})"
        )


def check_report_metadata(errors: list[str]) -> None:
    info_path = ROOT / "project_info.public.json"
    if not info_path.exists():
        errors.append("project_info.public.json missing")
        return

    try:
        info = json.loads(info_path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"Invalid JSON in project_info.public.json: {exc}")
        return

    mode = info.get("report_mode", "").lower()
    if mode != "public":
        errors.append(f"report_mode in project_info.public.json must be 'public'; got '{mode}'")

    required = {"project_title", "author_name", "course_name"}
    missing = [f for f in required if not info.get(f)]
    if missing:
        errors.append(f"Missing required fields in project_info.public.json: {', '.join(missing)}")

    placeholders = {
        "Your Name",
        "Your Student ID",
        "Instructor Name",
        "University Name",
        "YYYY-MM-DD",
        "Project Title",
        "نام و نام خانوادگی",
        "شماره دانشجویی",
        "نام استاد",
        "نام دانشگاه",
    }
    invalid = {k: v for k, v in info.items() if v in placeholders}
    if invalid:
        errors.append(f"Placeholder values in project_info.public.json: {', '.join(sorted(invalid))}")


def _safe_float(val: str | None) -> float:
    try:
        return float(val) if val else 0.0
    except (ValueError, TypeError):
        return 0.0


def _safe_int(val: str | None) -> int:
    try:
        return int(float(val)) if val else 0
    except (ValueError, TypeError):
        return 0


def check_result_consistency(errors: list[str]) -> None:
    test_manifest_path = ROOT / "maps" / "test" / "manifest.json"
    if not test_manifest_path.exists():
        errors.append(f"Missing test manifest: {test_manifest_path}")
        return

    test_manifest = json.loads(test_manifest_path.read_text(encoding="utf-8"))
    num_maps = len(test_manifest)

    if not EXPERIMENT_CSV_PATH.exists():
        errors.append(f"Missing experiment CSV: {EXPERIMENT_CSV_PATH}")
        return

    with EXPERIMENT_CSV_PATH.open(encoding="utf-8", newline="") as h:
        raw_rows = list(csv.DictReader(h))

    expected_rows = num_maps * 3
    if len(raw_rows) != expected_rows:
        errors.append(f"Expected {expected_rows} experiment rows ({num_maps} maps * 3 agents); found {len(raw_rows)}")
        return

    expected_pairs = {(entry["map_id"], agent) for entry in test_manifest for agent in ("astar", "rule", "genetic")}

    actual_pairs = [(row["map_id"], row["agent"]) for row in raw_rows]

    if len(actual_pairs) != len(set(actual_pairs)):
        errors.append("Duplicate map_id/agent rows found.")

    missing_pairs = expected_pairs - set(actual_pairs)
    extra_pairs = set(actual_pairs) - expected_pairs

    if missing_pairs:
        errors.append(f"Missing map/agent rows: {missing_pairs}")

    if extra_pairs:
        errors.append(f"Unexpected map/agent rows: {extra_pairs}")

    manifest_difficulties = {entry["map_id"]: entry["difficulty"] for entry in test_manifest}
    for row in raw_rows:
        if row["map_id"] in manifest_difficulties and row["difficulty"] != manifest_difficulties[row["map_id"]]:
            errors.append(
                f"Difficulty mismatch for {row['map_id']}: {row['difficulty']} != {manifest_difficulties[row['map_id']]}"
            )

    by_agent: dict[str, list[dict[str, str]]] = defaultdict(list)
    by_diff: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for r in raw_rows:
        by_agent[r["agent"]].append(r)
        by_diff[(r["agent"], r["difficulty"])].append(r)

    def _mean(rows: list[dict[str, str]], key: str) -> float:
        values = [_safe_float(r.get(key)) for r in rows]
        return sum(values) / len(values) if values else 0.0

    def compute_summary(agent: str, group: list[dict[str, str]]) -> dict[str, float | int]:
        successes = [r for r in group if str(r.get("success", "")).lower() in ("1", "true")]
        episodes = len(group)
        return {
            "episodes": episodes,
            "successes": len(successes),
            "success_rate": round(100.0 * len(successes) / episodes, 2) if episodes else 0.0,
            "average_score_all": round(_mean(group, "score"), 2),
            "average_score_delta_all": round(_mean(group, "score_delta"), 2),
            "average_remaining_health_all": round(_mean(group, "remaining_health"), 2),
            "average_steps_all": round(_mean(group, "steps"), 2),
            "average_steps_success": round(_mean(successes, "steps"), 2),
            "average_score_success": round(_mean(successes, "score"), 2),
            "average_pit_entries": round(_mean(group, "pit_entries"), 3),
            "wumpus_deaths": sum(
                1
                for r in group
                if str(r.get("wumpus_death", "")).lower() in ("1", "true")
                or r.get("termination_reason") == "wumpus_killed"
            ),
            "max_steps_failures": sum(1 for r in group if r.get("termination_reason") == "max_steps"),
            "average_runtime_ms": round(_mean(group, "runtime_ms"), 4),
            "average_expanded_nodes": round(_mean(group, "expanded_nodes"), 2),
        }

    computed_summary = {agent: compute_summary(agent, group) for agent, group in by_agent.items()}

    def validate_csv(path: Path, expected: dict[str, dict[str, float | int]], key_getter: callable, name: str):
        if not path.exists():
            errors.append(f"Missing required artifact: {path}")
            return
        with path.open(encoding="utf-8", newline="") as h:
            rows = list(csv.DictReader(h))

        actual_keys = [key_getter(row) for row in rows]
        if len(actual_keys) != len(set(actual_keys)):
            errors.append(f"{name} contains duplicate keys.")

        missing = set(expected) - set(actual_keys)
        extra = set(actual_keys) - set(expected)

        if missing:
            errors.append(f"{name} missing rows: {sorted(missing)}")
        if extra:
            errors.append(f"{name} unexpected rows: {sorted(extra)}")

        for row in rows:
            key = key_getter(row)
            comp = expected.get(key)
            if not comp:
                continue
            missing_fields = set(comp) - set(row)
            if missing_fields:
                errors.append(f"{name} row '{key}' is missing fields: {sorted(missing_fields)}")
                continue
            for field in comp:
                csv_val = float(row[field])
                calc_val = float(comp[field])
                tolerance = 1.0 if field == "average_runtime_ms" else 1e-2
                if abs(csv_val - calc_val) > tolerance:
                    errors.append(
                        f"{name} metric mismatch for '{key}' field '{field}': CSV={csv_val}, computed={calc_val}"
                    )

    validate_csv(SUMMARY_CSV_PATH, computed_summary, lambda r: r["agent"], "Summary CSV")

    diff_path = ROOT / "results" / "final" / "difficulty_results.csv"
    computed_diff = {f"{agent}-{diff}": compute_summary(agent, group) for (agent, diff), group in by_diff.items()}
    validate_csv(diff_path, computed_diff, lambda r: f"{r['agent']}-{r['difficulty']}", "Difficulty CSV")

    if FINAL_REPORT_HTML.exists():
        html_text = FINAL_REPORT_HTML.read_text(encoding="utf-8")
        if SUMMARY_CSV_PATH.exists():
            with SUMMARY_CSV_PATH.open(encoding="utf-8", newline="") as h:
                summary_rows = list(csv.DictReader(h))

            for row in summary_rows:
                agent = row["agent"]
                rate_str = row["success_rate"]
                row_pattern = rf"<tr><td>{agent}</td><td>{rate_str}%</td>"
                if not re.search(row_pattern, html_text):
                    errors.append(
                        f"Success rate {rate_str}% for agent '{agent}' not matched in HTML table of {FINAL_REPORT_HTML.name}"
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

    check_git_tracking(errors)
    check_canonical_artifacts(errors)
    check_weight_integrity(errors)
    check_training_metadata_consistency(errors)
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
