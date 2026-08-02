from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import subprocess
import time
from collections import Counter, defaultdict
from importlib.metadata import version
from pathlib import Path
from typing import Any, Iterable

import matplotlib
import matplotlib.pyplot as plt

from wumpus_world.map_generator import generate_test_suite
from wumpus_world.runner import run_episode

matplotlib.use("Agg")

PROJECT_VERSION = version("wumpus-world-genetic")

AGENTS = ("astar", "rule", "genetic")
METRIC_FIELDS = (
    "map_id",
    "difficulty",
    "agent",
    "success",
    "score",
    "score_delta",
    "initial_health",
    "remaining_health",
    "steps",
    "pit_entries",
    "collected_gold",
    "wumpus_death",
    "termination_reason",
    "runtime_ms",
    "expanded_nodes",
    "plan_cost",
    "error",
)


def _load_manifest(test_dir: Path) -> dict[str, dict[str, Any]]:
    path = test_dir / "manifest.json"
    if not path.exists():
        raise FileNotFoundError(f"Missing test manifest: {path}")
    entries = json.loads(path.read_text(encoding="utf-8"))
    return {entry["map_id"]: entry for entry in entries}


def _safe_number(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def run_benchmark(
    *,
    test_dir: str | Path = "maps/test",
    results_dir: str | Path = "results/final",
    max_steps: int = 250,
    weights_path: str = "best_weights.json",
    timing_repeats: int = 3,
) -> list[dict[str, Any]]:
    if timing_repeats < 1:
        raise ValueError("timing_repeats must be positive.")
    test_dir = Path(test_dir)
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    manifest = _load_manifest(test_dir)
    map_files = sorted(test_dir.glob("test_*.txt"))
    if not map_files:
        raise FileNotFoundError(f"No test maps found in {test_dir}")

    rows: list[dict[str, Any]] = []
    for map_path in map_files:
        map_id = map_path.stem
        if map_id not in manifest:
            raise KeyError(f"Map {map_id} is missing from manifest.json")
        difficulty = manifest[map_id]["difficulty"]
        for agent in AGENTS:
            runtimes: list[float] = []
            first_result: dict[str, Any] | None = None
            for _ in range(timing_repeats):
                started = time.perf_counter()
                result = run_episode(
                    str(map_path),
                    agent,
                    max_steps=max_steps,
                    weights_path=weights_path,
                    verbose=False,
                )
                runtimes.append((time.perf_counter() - started) * 1000)
                if first_result is None:
                    first_result = result
            assert first_result is not None
            reason = str(first_result.get("termination_reason", "unknown"))
            rows.append(
                {
                    "map_id": map_id,
                    "difficulty": difficulty,
                    "agent": agent,
                    "success": int(bool(first_result.get("success", False))),
                    "score": int(_safe_number(first_result.get("score"))),
                    "score_delta": int(_safe_number(first_result.get("score_delta"))),
                    "initial_health": int(_safe_number(first_result.get("initial_health"))),
                    "remaining_health": int(_safe_number(first_result.get("remaining_health"))),
                    "steps": int(_safe_number(first_result.get("steps"))),
                    "pit_entries": int(_safe_number(first_result.get("pit_entries"))),
                    "collected_gold": int(_safe_number(first_result.get("collected_gold"))),
                    "wumpus_death": int(reason == "wumpus"),
                    "termination_reason": reason,
                    "runtime_ms": round(statistics.median(runtimes), 4),
                    "expanded_nodes": int(_safe_number(first_result.get("expanded_nodes"))),
                    "plan_cost": int(_safe_number(first_result.get("plan_cost"))),
                    "error": first_result.get("error", ""),
                }
            )

    raw_path = results_dir / "experiment_results.csv"
    with raw_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=METRIC_FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return rows


def _mean(rows: Iterable[dict[str, Any]], key: str) -> float:
    values = [_safe_number(row.get(key)) for row in rows]
    return statistics.fmean(values) if values else 0.0


def _summary_row(agent: str, rows: list[dict[str, Any]]) -> dict[str, Any]:
    successes = [row for row in rows if int(row["success"])]
    success_count = len(successes)
    return {
        "agent": agent,
        "episodes": len(rows),
        "successes": success_count,
        "success_rate": round(100 * success_count / len(rows), 2) if rows else 0.0,
        "average_score_all": round(_mean(rows, "score"), 2),
        "average_score_delta_all": round(_mean(rows, "score_delta"), 2),
        "average_remaining_health_all": round(_mean(rows, "remaining_health"), 2),
        "average_steps_all": round(_mean(rows, "steps"), 2),
        "average_steps_success": round(_mean(successes, "steps"), 2),
        "average_score_success": round(_mean(successes, "score"), 2),
        "average_pit_entries": round(_mean(rows, "pit_entries"), 3),
        "wumpus_deaths": sum(int(row["wumpus_death"]) for row in rows),
        "max_steps_failures": sum(str(row["termination_reason"]) == "max_steps" for row in rows),
        "average_runtime_ms": round(_mean(rows, "runtime_ms"), 4),
        "average_expanded_nodes": round(_mean(rows, "expanded_nodes"), 2),
    }


def summarize(
    rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    by_agent: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_difficulty: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_agent[row["agent"]].append(row)
        by_difficulty[(row["agent"], row["difficulty"])].append(row)

    summary = [_summary_row(agent, by_agent[agent]) for agent in AGENTS]
    difficulty_summary: list[dict[str, Any]] = []
    for agent in AGENTS:
        for difficulty in ("easy", "medium", "hard"):
            group = by_difficulty[(agent, difficulty)]
            row = _summary_row(agent, group)
            row["difficulty"] = difficulty
            difficulty_summary.append(row)
    return summary, difficulty_summary


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _bar_chart(summary: list[dict[str, Any]], key: str, ylabel: str, output: Path) -> None:
    labels = [row["agent"] for row in summary]
    values = [float(row[key]) for row in summary]
    plt.figure(figsize=(7, 4.5))
    bars = plt.bar(labels, values)
    plt.ylabel(ylabel)
    plt.xlabel("Agent")
    plt.title(ylabel + " by agent")
    plt.grid(axis="y", alpha=0.25)
    for bar, value in zip(bars, values):
        plt.text(
            bar.get_x() + bar.get_width() / 2,
            bar.get_height(),
            f"{value:.2f}",
            ha="center",
            va="bottom",
        )
    plt.tight_layout()
    plt.savefig(output, dpi=160)
    plt.close()


def _difficulty_chart(difficulty_rows: list[dict[str, Any]], output: Path) -> None:
    difficulties = ("easy", "medium", "hard")
    x = list(range(len(difficulties)))
    width = 0.24
    plt.figure(figsize=(8, 4.8))
    for index, agent in enumerate(AGENTS):
        lookup = {row["difficulty"]: float(row["success_rate"]) for row in difficulty_rows if row["agent"] == agent}
        values = [lookup.get(level, 0.0) for level in difficulties]
        positions = [value + (index - 1) * width for value in x]
        plt.bar(positions, values, width=width, label=agent)
    plt.xticks(x, difficulties)
    plt.ylim(0, 105)
    plt.ylabel("Success rate (%)")
    plt.xlabel("Difficulty")
    plt.title("Success rate by difficulty")
    plt.legend()
    plt.grid(axis="y", alpha=0.25)
    plt.tight_layout()
    plt.savefig(output, dpi=160)
    plt.close()


def _failure_chart(rows: list[dict[str, Any]], output: Path) -> None:
    reasons = sorted({str(row["termination_reason"]) for row in rows if not int(row["success"])})
    if not reasons:
        reasons = ["none"]
    x = list(range(len(reasons)))
    width = 0.24
    plt.figure(figsize=(max(8, len(reasons) * 1.4), 4.8))
    for index, agent in enumerate(AGENTS):
        counts = Counter(
            str(row["termination_reason"]) for row in rows if row["agent"] == agent and not int(row["success"])
        )
        positions = [value + (index - 1) * width for value in x]
        plt.bar(
            positions,
            [counts.get(reason, 0) for reason in reasons],
            width=width,
            label=agent,
        )
    plt.xticks(x, reasons, rotation=25, ha="right")
    plt.ylabel("Episodes")
    plt.title("Failure reasons")
    plt.legend()
    plt.tight_layout()
    plt.savefig(output, dpi=160)
    plt.close()


def write_report(
    rows: list[dict[str, Any]],
    summary: list[dict[str, Any]],
    difficulty_summary: list[dict[str, Any]],
    results_dir: Path,
) -> None:
    success_winner = max(summary, key=lambda row: (row["success_rate"], row["average_score_all"]))
    online = [row for row in summary if row["agent"] in {"rule", "genetic"}]
    online_winner = max(online, key=lambda row: (row["success_rate"], row["average_score_all"]))
    lines = [
        f"WUMPUS WORLD VERSION {PROJECT_VERSION} - FINAL EXPERIMENT SUMMARY",
        "=" * 56,
        "",
        f"Episodes per agent: {summary[0]['episodes'] if summary else 0}",
        f"Best overall success rate: {success_winner['agent']} ({success_winner['success_rate']:.2f}%)",
        f"Best online agent: {online_winner['agent']} ({online_winner['success_rate']:.2f}%)",
        "",
        "OVERALL RESULTS",
        "-" * 56,
    ]
    for row in summary:
        lines.append(
            f"{row['agent']:8s} | success={row['success_rate']:6.2f}% | "
            f"score_all={row['average_score_all']:7.2f} | "
            f"steps_all={row['average_steps_all']:7.2f} | "
            f"steps_success={row['average_steps_success']:7.2f} | "
            f"runtime={row['average_runtime_ms']:8.4f} ms"
        )

    lines.extend(
        [
            "",
            "INTERPRETATION AND LIMITATIONS",
            "-" * 56,
            "1. A* has full map information and is an oracle/upper-bound baseline.",
            "2. Rule-based and genetic agents receive the same local observations.",
            "3. The genetic method is hybrid: GA weights guide exploration, while a knowledge base and safe-return policy are shared components.",
            "4. Initial health is identical across difficulty levels, so score comparison is not biased by starting health.",
            "5. Average successful steps is reported separately; failed early episodes no longer make an agent look artificially faster.",
            "6. Runtime is the median of repeated complete episodes, not a single noisy measurement.",
            "7. Test maps are deterministic and separate from the training maps.",
        ]
    )
    failures = Counter(str(row["termination_reason"]) for row in rows if not int(row["success"]))
    lines.extend(["", "FAILURE COUNTS", "-" * 56])
    if failures:
        for reason, count in failures.most_common():
            lines.append(f"{reason}: {count}")
    else:
        lines.append("none")

    (results_dir / "experiment_summary.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_run_metadata(
    results_dir: Path,
    test_seed: int = 20260730,
    per_difficulty: int = 10,
    max_steps: int = 250,
    timing_repeats: int = 3,
    weights_path: str = "best_weights.json",
) -> None:
    results_dir.mkdir(parents=True, exist_ok=True)
    git_commit = "unknown"
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout.strip():
            git_commit = proc.stdout.strip()
    except Exception:
        pass

    weights_file = Path(weights_path)
    weights_sha256 = ""
    best_fitness = 0.0
    if weights_file.exists():
        data = weights_file.read_bytes()
        weights_sha256 = hashlib.sha256(data).hexdigest()
        try:
            weights_json = json.loads(data.decode("utf-8"))
            best_fitness = float(weights_json.get("metadata", {}).get("best_fitness", 0.0))
        except Exception:
            pass

    metadata = {
        "project_version": PROJECT_VERSION,
        "git_commit": git_commit,
        "training_seed": 17,
        "training_map_seed": 1701,
        "test_seed": test_seed,
        "training_maps": 12,
        "test_maps": per_difficulty * 3,
        "maps_per_difficulty": per_difficulty,
        "population": 24,
        "generations": 24,
        "mutation_rate": 0.1,
        "max_steps": max_steps,
        "timing_repeats": timing_repeats,
        "weights_sha256": weights_sha256,
        "best_fitness": best_fitness,
    }
    (results_dir / "run_metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def analyze_and_export(
    rows: list[dict[str, Any]],
    results_dir: str | Path = "results/final",
    test_seed: int = 20260730,
    per_difficulty: int = 10,
    max_steps: int = 250,
    timing_repeats: int = 3,
    weights_path: str = "best_weights.json",
) -> None:
    results_dir = Path(results_dir)
    results_dir.mkdir(parents=True, exist_ok=True)
    summary, difficulty_summary = summarize(rows)
    _write_csv(results_dir / "summary_results.csv", summary)
    _write_csv(results_dir / "difficulty_results.csv", difficulty_summary)
    _bar_chart(summary, "success_rate", "Success rate (%)", results_dir / "success_rate.png")
    _bar_chart(
        summary,
        "average_score_all",
        "Average score (all episodes)",
        results_dir / "average_score.png",
    )
    _bar_chart(
        summary,
        "average_steps_success",
        "Average steps (successful episodes)",
        results_dir / "average_steps_success.png",
    )
    _bar_chart(
        summary,
        "average_remaining_health_all",
        "Average remaining health",
        results_dir / "remaining_health.png",
    )
    _bar_chart(
        summary,
        "average_runtime_ms",
        "Median episode runtime (ms)",
        results_dir / "runtime.png",
    )
    _difficulty_chart(difficulty_summary, results_dir / "success_by_difficulty.png")
    _failure_chart(rows, results_dir / "failure_reasons.png")
    write_report(rows, summary, difficulty_summary, results_dir)
    write_run_metadata(
        results_dir,
        test_seed=test_seed,
        per_difficulty=per_difficulty,
        max_steps=max_steps,
        timing_repeats=timing_repeats,
        weights_path=weights_path,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark A*, rule-based, and hybrid genetic agents.")
    parser.add_argument("--test-dir", default="maps/test")
    parser.add_argument("--results-dir", default="results/final")
    parser.add_argument("--per-difficulty", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260730)
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument("--weights", default="best_weights.json")
    parser.add_argument("--timing-repeats", type=int, default=3)
    parser.add_argument("--skip-generate", action="store_true")
    args = parser.parse_args()

    if not args.skip_generate:
        manifest = generate_test_suite(
            args.test_dir,
            maps_per_difficulty=args.per_difficulty,
            seed=args.seed,
        )
        print(f"Generated {len(manifest)} test maps.")

    rows = run_benchmark(
        test_dir=args.test_dir,
        results_dir=args.results_dir,
        max_steps=args.max_steps,
        weights_path=args.weights,
        timing_repeats=args.timing_repeats,
    )
    analyze_and_export(
        rows,
        results_dir=args.results_dir,
        test_seed=args.seed,
        per_difficulty=args.per_difficulty,
        max_steps=args.max_steps,
        timing_repeats=args.timing_repeats,
        weights_path=args.weights,
    )
    print(f"Completed {len(rows)} episodes.")
    print(f"Results saved in {args.results_dir}")


if __name__ == "__main__":
    main()
