from __future__ import annotations

import argparse

from wumpus_world.runner import run_episode


def main() -> None:
    parser = argparse.ArgumentParser(description="Wumpus World - final version 8")
    parser.add_argument("--map", default="maps/sample_01.txt")
    parser.add_argument(
        "--agent",
        choices=("astar", "rule", "genetic", "random"),
        default="genetic",
    )
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument("--weights", default="best_weights.json")
    parser.add_argument("--use-default-weights", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()
    run_episode(
        args.map,
        args.agent,
        args.max_steps,
        weights_path=args.weights,
        use_default_weights=args.use_default_weights,
        verbose=not args.quiet,
    )


if __name__ == "__main__":
    main()
