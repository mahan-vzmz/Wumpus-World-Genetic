from __future__ import annotations

from pathlib import Path
from statistics import mean

from genetic_agent import GeneticWeights
from genetic_algorithm import evaluate_episode
from map_parser import load_map


def evaluate_set(label: str, weights: GeneticWeights, paths: list[Path]) -> None:
    results = [
        evaluate_episode(load_map(path), weights, max_steps=250) for path in paths
    ]
    print(f"\n{label}")
    print("map,success,fitness,steps,health,pits,reason")
    for path, result in zip(paths, results):
        print(
            f"{path.name},{result.success},{result.fitness:.2f},{result.steps},"
            f"{result.remaining_health},{result.pit_entries},"
            f"{result.termination_reason}"
        )
    print(
        f"summary: success_rate={100 * mean(r.success for r in results):.1f}% "
        f"average_fitness={mean(r.fitness for r in results):.2f} "
        f"average_steps={mean(r.steps for r in results):.2f}"
    )


def main() -> None:
    paths = sorted(Path("maps/training").glob("training_*.txt"))
    if not paths:
        raise SystemExit("No training maps found.")
    evaluate_set("Default hand-written weights", GeneticWeights(), paths)
    evaluate_set(
        "Evolved weights", GeneticWeights.load("best_weights.json"), paths
    )


if __name__ == "__main__":
    main()
