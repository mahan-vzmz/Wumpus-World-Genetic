from __future__ import annotations

import argparse

from wumpus_world.runner import run_episode


def main() -> None:
    parser = argparse.ArgumentParser(description="Run all three final agents on one map.")
    parser.add_argument("--map", default="maps/sample_01.txt")
    parser.add_argument("--max-steps", type=int, default=250)
    parser.add_argument("--weights", default="best_weights.json")
    args = parser.parse_args()

    print("agent,success,score,steps,health,pits,reason")
    for agent in ("astar", "rule", "genetic"):
        result = run_episode(
            args.map,
            agent,
            max_steps=args.max_steps,
            weights_path=args.weights,
            verbose=False,
        )
        print(
            f"{agent},{result['success']},{result['score']},{result['steps']},"
            f"{result['remaining_health']},{result['pit_entries']},"
            f"{result['termination_reason']}"
        )


if __name__ == "__main__":
    main()
