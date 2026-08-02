from __future__ import annotations

import argparse
from pathlib import Path

from wumpus_world.runner import run_episode

PROJECT_ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all three final agents on one map.")
    parser.add_argument("--map", default=str(PROJECT_ROOT / "maps" / "sample_01.txt"))
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument("--weights", default=str(PROJECT_ROOT / "best_weights.json"))
    args = parser.parse_args()

    has_error = False
    print("agent,success,score,steps,health,pits,reason")
    for agent in ("astar", "rule", "genetic"):
        result = run_episode(
            args.map,
            agent,
            max_steps=args.max_steps,
            weights_path=args.weights,
            verbose=False,
        )
        if result.get("termination_reason") == "initialization_error":
            has_error = True
        print(
            f"{agent},{result['success']},{result['score']},{result['steps']},"
            f"{result['remaining_health']},{result['pit_entries']},"
            f"{result['termination_reason']}"
        )

    if has_error:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
