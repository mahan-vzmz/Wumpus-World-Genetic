from __future__ import annotations
from pathlib import Path
from experiment import run_benchmark, summarize
from main import run_episode
from wumpus_world.map_generator import generate_test_suite


def test_summary_separates_successful_steps() -> None:
    rows = [
        {"agent": "astar", "difficulty": "easy", "success": 1, "score": 100, "score_delta": -20, "remaining_health": 90, "steps": 10, "pit_entries": 0, "wumpus_death": 0, "runtime_ms": 2, "expanded_nodes": 20, "termination_reason": "escaped_with_gold"},
        {"agent": "astar", "difficulty": "easy", "success": 0, "score": 0, "score_delta": -120, "remaining_health": 0, "steps": 2, "pit_entries": 0, "wumpus_death": 1, "runtime_ms": 4, "expanded_nodes": 30, "termination_reason": "wumpus"},
        {"agent": "rule", "difficulty": "easy", "success": 1, "score": 80, "score_delta": -40, "remaining_health": 70, "steps": 30, "pit_entries": 0, "wumpus_death": 0, "runtime_ms": 3, "expanded_nodes": 0, "termination_reason": "escaped_with_gold"},
        {"agent": "genetic", "difficulty": "easy", "success": 1, "score": 85, "score_delta": -35, "remaining_health": 75, "steps": 25, "pit_entries": 0, "wumpus_death": 0, "runtime_ms": 2, "expanded_nodes": 0, "termination_reason": "escaped_with_gold"},
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
