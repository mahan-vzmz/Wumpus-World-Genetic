from __future__ import annotations

import argparse
import sys

from wumpus_world.resources import default_map_path, default_weights_path
from wumpus_world.runner import run_episode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all three final agents on one map.")
    parser.add_argument("--map", default=None)
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument("--weights", default=None)
    args = parser.parse_args()

    map_path = args.map if args.map is not None else default_map_path()
    weights_path = args.weights if args.weights is not None else default_weights_path()

    has_error = False
    print("agent,success,score,steps,health,pits,reason")
    for agent in ("astar", "rule", "genetic"):
        result = run_episode(
            map_path,
            agent,
            max_steps=args.max_steps,
            weights_path=weights_path,
            verbose=False,
        )
        if result.get("termination_reason") == "initialization_error":
            has_error = True
            print(
                f"{agent}: {result.get('error', 'Initialization failed.')}",
                file=sys.stderr,
            )
        print(
            f"{agent},{result['success']},{result['score']},{result['steps']},"
            f"{result['remaining_health']},{result['pit_entries']},"
            f"{result['termination_reason']}"
        )

    if has_error:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
