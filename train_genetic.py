from __future__ import annotations
import argparse
from pathlib import Path
from genetic_algorithm import (
    GeneticTrainer,
    load_training_configs,
    plot_history,
    save_training_artifacts,
)
from map_generator import generate_training_suite


def main() -> None:
    parser = argparse.ArgumentParser(description="Train Wumpus hybrid genetic weights.")
    parser.add_argument("--maps", nargs="+")
    parser.add_argument("--population", type=int, default=24)
    parser.add_argument("--generations", type=int, default=24)
    parser.add_argument("--mutation-rate", type=float, default=0.10)
    parser.add_argument("--mutation-sigma", type=float, default=2.0)
    parser.add_argument("--elite-count", type=int, default=2)
    parser.add_argument("--tournament-size", type=int, default=3)
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument("--patience", type=int, default=8)
    parser.add_argument("--seed", type=int, default=17)
    parser.add_argument("--output", default="best_weights.json")
    parser.add_argument("--history", default="results/genetic_history.csv")
    parser.add_argument("--summary", default="results/genetic_training_summary.json")
    parser.add_argument("--plot", default="results/genetic_fitness.png")
    parser.add_argument("--regenerate-training-maps", action="store_true")
    args = parser.parse_args()

    if args.regenerate_training_maps:
        generate_training_suite()
    paths = args.maps or [
        str(path) for path in sorted(Path("maps/training").glob("training_*.txt"))
    ]
    if not paths:
        raise SystemExit(
            "No training maps found. Run with --regenerate-training-maps first."
        )

    trainer = GeneticTrainer(
        load_training_configs(paths),
        population_size=args.population,
        generations=args.generations,
        mutation_rate=args.mutation_rate,
        mutation_sigma=args.mutation_sigma,
        elite_count=args.elite_count,
        tournament_size=args.tournament_size,
        max_steps=args.max_steps,
        seed=args.seed,
        patience=args.patience,
    )
    result = trainer.train(verbose=True)
    save_training_artifacts(
        result,
        weights_path=args.output,
        history_csv_path=args.history,
        summary_json_path=args.summary,
    )
    plot_history(result, args.plot)
    print("\nTraining complete")
    print(f"best_fitness={result.best_fitness:.2f}")
    print(f"generations_run={len(result.history)}")
    print(f"weights={args.output}")


if __name__ == "__main__":
    main()
