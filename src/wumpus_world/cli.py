from __future__ import annotations

import argparse

from wumpus_world.runner import run_episode


from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Wumpus World")
    parser.add_argument("--map", default=str(PROJECT_ROOT / "maps" / "sample_01.txt"))
    parser.add_argument(
        "--agent",
        choices=("astar", "rule", "genetic", "random"),
        default="genetic",
    )
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument("--weights", default=str(PROJECT_ROOT / "best_weights.json"))
    parser.add_argument("--use-default-weights", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    result = run_episode(
        args.map,
        args.agent,
        args.max_steps,
        weights_path=args.weights,
        use_default_weights=args.use_default_weights,
        verbose=not args.quiet,
    )

    if result.get("termination_reason") == "initialization_error":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
