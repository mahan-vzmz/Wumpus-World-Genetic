from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from experiment import run_benchmark, summarize
from wumpus_world.map_generator import generate_test_suite
from wumpus_world.runner import run_episode


def test_summary_separates_successful_steps() -> None:
    rows = [
        {
            "agent": "astar",
            "difficulty": "easy",
            "success": 1,
            "score": 100,
            "score_delta": -20,
            "remaining_health": 90,
            "steps": 10,
            "pit_entries": 0,
            "wumpus_death": 0,
            "runtime_ms": 2,
            "expanded_nodes": 20,
            "termination_reason": "escaped_with_gold",
        },
        {
            "agent": "astar",
            "difficulty": "easy",
            "success": 0,
            "score": 0,
            "score_delta": -120,
            "remaining_health": 0,
            "steps": 2,
            "pit_entries": 0,
            "wumpus_death": 1,
            "runtime_ms": 4,
            "expanded_nodes": 30,
            "termination_reason": "wumpus",
        },
        {
            "agent": "rule",
            "difficulty": "easy",
            "success": 1,
            "score": 80,
            "score_delta": -40,
            "remaining_health": 70,
            "steps": 30,
            "pit_entries": 0,
            "wumpus_death": 0,
            "runtime_ms": 3,
            "expanded_nodes": 0,
            "termination_reason": "escaped_with_gold",
        },
        {
            "agent": "genetic",
            "difficulty": "easy",
            "success": 1,
            "score": 85,
            "score_delta": -35,
            "remaining_health": 75,
            "steps": 25,
            "pit_entries": 0,
            "wumpus_death": 0,
            "runtime_ms": 2,
            "expanded_nodes": 0,
            "termination_reason": "escaped_with_gold",
        },
    ]
    summary, _ = summarize(rows)
    astar = next(row for row in summary if row["agent"] == "astar")
    assert astar["success_rate"] == 50.0
    assert astar["average_steps_all"] == 6.0
    assert astar["average_steps_success"] == 10.0


def test_run_episode_records_max_steps() -> None:
    result = run_episode(
        "maps/sample_rule_safe.txt",
        "random",
        max_steps=1,
        verbose=False,
    )
    assert result["termination_reason"] == "max_steps"
    assert result["success"] is False


def test_small_benchmark_writes_rows(tmp_path: Path) -> None:
    test_dir = tmp_path / "maps"
    results_dir = tmp_path / "results"
    generate_test_suite(test_dir, maps_per_difficulty=1, seed=88)
    rows = run_benchmark(
        test_dir=test_dir,
        results_dir=results_dir,
        max_steps=100,
        timing_repeats=1,
    )
    assert len(rows) == 9
    assert (results_dir / "experiment_results.csv").exists()
    assert all(row["termination_reason"] != "None" for row in rows)


def test_missing_gene_is_detected(tmp_path: Path) -> None:
    import json

    from tools.check_repository_consistency import check_training_metadata_consistency

    root_weights = tmp_path / "best_weights.json"
    root_weights.write_text(json.dumps({"genes": {"gene1": 1.0, "gene2": 2.0}}))

    training_summary = tmp_path / "summary.json"
    training_summary.write_text(
        json.dumps(
            {
                "seed": 1,
                "map_count": 1,
                "population": 1,
                "requested_generations": 1,
                "generations_run": 1,
                "mutation_rate": 0.1,
                "mutation_sigma": 0.1,
                "crossover_rate": 0.1,
                "patience": 1,
                "elite_count": 1,
                "tournament_size": 1,
                "max_steps": 1,
                "best_fitness": 1.0,
                "best_weights": {"gene1": 1.0},
            }
        )
    )

    run_meta = tmp_path / "run_meta.json"
    run_meta.write_text(
        json.dumps(
            {
                "training_seed": 1,
                "training_maps": 1,
                "population": 1,
                "requested_generations": 1,
                "generations_run": 1,
                "mutation_rate": 0.1,
                "mutation_sigma": 0.1,
                "crossover_rate": 0.1,
                "patience": 1,
                "elite_count": 1,
                "tournament_size": 1,
                "training_max_steps": 1,
                "best_fitness": 1.0,
            }
        )
    )

    with (
        patch("tools.check_repository_consistency.ROOT_WEIGHTS", root_weights),
        patch("tools.check_repository_consistency.TRAINING_SUMMARY_PATH", training_summary),
        patch("tools.check_repository_consistency.RUN_METADATA_PATH", run_meta),
    ):
        errors = []
        check_training_metadata_consistency(errors)
        assert any("Weight genes mismatch" in e for e in errors)


def test_difficulty_summary_matches_raw_rows() -> None:
    from experiment import _summary_row

    rows = [
        {
            "success": 1,
            "score": 10,
            "score_delta": -1,
            "remaining_health": 10,
            "steps": 5,
            "pit_entries": 0,
            "wumpus_death": 0,
            "termination_reason": "won",
            "runtime_ms": 1,
            "expanded_nodes": 1,
        },
        {
            "success": 0,
            "score": 0,
            "score_delta": -10,
            "remaining_health": 0,
            "steps": 2,
            "pit_entries": 0,
            "wumpus_death": 1,
            "termination_reason": "wumpus",
            "runtime_ms": 1,
            "expanded_nodes": 1,
        },
    ]
    summary = _summary_row("agent", rows)
    assert summary["episodes"] == 2
    assert summary["successes"] == 1
    assert summary["success_rate"] == 50.0
    assert summary["average_score_all"] == 5.0
    assert summary["average_steps_all"] == 3.5
    assert summary["average_steps_success"] == 5.0
    assert summary["wumpus_deaths"] == 1


def test_duplicate_map_agent_row_is_rejected(tmp_path: Path) -> None:
    import csv
    import json

    from tools.check_repository_consistency import check_result_consistency

    test_manifest = tmp_path / "maps" / "test" / "manifest.json"
    test_manifest.parent.mkdir(parents=True)
    test_manifest.write_text(json.dumps([{"map_id": "m1", "difficulty": "easy"}]))

    exp_csv = tmp_path / "experiment.csv"

    # Total expected is 3 rows. We will provide 2 astar and 1 genetic (missing rule)
    with exp_csv.open("w", newline="") as h:
        writer = csv.DictWriter(
            h,
            fieldnames=[
                "agent",
                "difficulty",
                "map_id",
                "success",
                "score",
                "score_delta",
                "remaining_health",
                "steps",
                "pit_entries",
                "wumpus_death",
                "termination_reason",
                "runtime_ms",
                "expanded_nodes",
            ],
        )
        writer.writeheader()
        writer.writerow(
            {
                "agent": "astar",
                "difficulty": "easy",
                "map_id": "m1",
                "success": 1,
                "score": 10,
                "score_delta": 0,
                "remaining_health": 10,
                "steps": 1,
                "pit_entries": 0,
                "wumpus_death": 0,
                "termination_reason": "",
                "runtime_ms": 1,
                "expanded_nodes": 1,
            }
        )
        writer.writerow(
            {
                "agent": "astar",
                "difficulty": "easy",
                "map_id": "m1",
                "success": 1,
                "score": 10,
                "score_delta": 0,
                "remaining_health": 10,
                "steps": 1,
                "pit_entries": 0,
                "wumpus_death": 0,
                "termination_reason": "",
                "runtime_ms": 1,
                "expanded_nodes": 1,
            }
        )
        writer.writerow(
            {
                "agent": "genetic",
                "difficulty": "easy",
                "map_id": "m1",
                "success": 1,
                "score": 10,
                "score_delta": 0,
                "remaining_health": 10,
                "steps": 1,
                "pit_entries": 0,
                "wumpus_death": 0,
                "termination_reason": "",
                "runtime_ms": 1,
                "expanded_nodes": 1,
            }
        )

    with (
        patch("tools.check_repository_consistency.ROOT", tmp_path),
        patch("tools.check_repository_consistency.EXPERIMENT_CSV_PATH", exp_csv),
    ):
        errors = []
        check_result_consistency(errors)
        assert any("Duplicate map_id/agent rows found." in e for e in errors)
        assert any("Missing map/agent rows" in e for e in errors)


def test_canonical_json_sha256_ignores_crlf(tmp_path: Path) -> None:
    from tools.check_repository_consistency import canonical_json_sha256

    lf_file = tmp_path / "lf.json"
    lf_file.write_bytes(b'{"key": "value"}\n')
    crlf_file = tmp_path / "crlf.json"
    crlf_file.write_bytes(b'{"key": "value"}\r\n')

    assert canonical_json_sha256(lf_file) == canonical_json_sha256(crlf_file)
    assert canonical_json_sha256(lf_file) != ""


def test_canonical_json_sha256_fallback_ignores_crlf(tmp_path: Path) -> None:
    from tools.check_repository_consistency import canonical_json_sha256

    lf_file = tmp_path / "lf.txt"
    lf_file.write_bytes(b'not a json\n')
    crlf_file = tmp_path / "crlf.txt"
    crlf_file.write_bytes(b'not a json\r\n')

    assert canonical_json_sha256(lf_file) == canonical_json_sha256(crlf_file)
    assert canonical_json_sha256(lf_file) != ""


def test_custom_maps_provenance_hash(tmp_path: Path) -> None:
    import json
    import subprocess
    import sys

    # Create dummy maps
    valid_map = (
        "********\n"
        "********\n"
        "********\n"
        "***G****\n"
        "********\n"
        "********\n"
        "********\n"
        "********\n"
        "health=120\n"
        "gold=50\n"
        "pit=10\n"
        "exit=8,8\n"
    )
    m1 = tmp_path / "m1.txt"
    m1.write_text(valid_map)
    m2 = tmp_path / "m2.txt"
    m2.write_text(valid_map)

    result = subprocess.run(
        [
            sys.executable,
            "train_genetic.py",
            "--maps",
            str(m1),
            str(m2),
            "--generations",
            "1",
            "--population",
            "4",
            "--summary",
            str(tmp_path / "summary.json"),
            "--output",
            str(tmp_path / "best_weights.json"),
            "--history",
            str(tmp_path / "history.csv"),
            "--plot",
            str(tmp_path / "plot.png"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0

    summary = json.loads((tmp_path / "summary.json").read_text())
    assert summary["training_map_source"] == "custom"

    import hashlib
    digest = hashlib.sha256()
    for p in sorted([m1, m2], key=lambda x: str(x)):
        digest.update(p.name.encode("utf-8"))
        digest.update(p.read_bytes())

    assert summary["training_map_manifest_sha256"] == digest.hexdigest()
