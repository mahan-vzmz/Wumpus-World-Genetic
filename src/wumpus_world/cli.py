from __future__ import annotations

import argparse
import sys

from wumpus_world.resources import default_map_path, default_weights_path
from wumpus_world.runner import run_episode


def main() -> None:
    parser = argparse.ArgumentParser(description="Wumpus World")
    parser.add_argument("--map", default=None)
    parser.add_argument(
        "--agent",
        choices=("astar", "rule", "genetic", "random"),
        default="genetic",
    )
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument("--weights", default=None)
    parser.add_argument("--use-default-weights", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    map_path = args.map if args.map is not None else default_map_path()
    weights_path = args.weights if args.weights is not None else default_weights_path()

    result = run_episode(
        map_path,
        args.agent,
        args.max_steps,
        weights_path=weights_path,
        use_default_weights=args.use_default_weights,
        verbose=not args.quiet,
    )

    if result.get("termination_reason") == "initialization_error":
        print(result.get("error", "Initialization failed."), file=sys.stderr)
        raise SystemExit(2)


if __name__ == "__main__":
    main()
