from __future__ import annotations

import argparse
import json
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from wumpus_world.agents.astar_agent import AStarAgent
from wumpus_world.map_parser import GRID_SIZE, load_map

Position = tuple[int, int]


@dataclass(frozen=True)
class GeneratedMapInfo:
    map_id: str
    difficulty: str
    seed: int
    initial_health: int
    gold_score: int
    pit_penalty: int
    exit_position: Position
    gold_position: Position
    walls: int
    pits: int
    wumpus: int
    protected_path_length: int
    astar_plan_length: int


def _neighbors(position: Position) -> list[Position]:
    row, col = position
    result: list[Position] = []
    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nxt = (row + dr, col + dc)
        if 0 <= nxt[0] < GRID_SIZE and 0 <= nxt[1] < GRID_SIZE:
            result.append(nxt)
    return result


def _random_shortest_path(start: Position, goal: Position, rng: random.Random) -> list[Position]:
    current = start
    path = [current]
    moves: list[tuple[int, int]] = []
    row_delta = goal[0] - start[0]
    col_delta = goal[1] - start[1]
    moves.extend([(1 if row_delta > 0 else -1, 0)] * abs(row_delta))
    moves.extend([(0, 1 if col_delta > 0 else -1)] * abs(col_delta))
    rng.shuffle(moves)
    for dr, dc in moves:
        current = current[0] + dr, current[1] + dc
        path.append(current)
    return path


def _add_detours(path: list[Position], detours: int, rng: random.Random) -> list[Position]:
    result = list(path)
    attempts = 0
    added = 0
    while added < detours and attempts < 100:
        attempts += 1
        if len(result) < 2:
            break
        index = rng.randrange(len(result) - 1)
        first, second = result[index], result[index + 1]
        candidates: list[tuple[Position, Position]] = []
        if first[0] == second[0]:
            for offset in (-1, 1):
                candidates.append(
                    (
                        (first[0] + offset, first[1]),
                        (second[0] + offset, second[1]),
                    )
                )
        else:
            for offset in (-1, 1):
                candidates.append(
                    (
                        (first[0], first[1] + offset),
                        (second[0], second[1] + offset),
                    )
                )
        rng.shuffle(candidates)
        for side1, side2 in candidates:
            if not all(0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE for r, c in (side1, side2)):
                continue
            if side1 in result or side2 in result:
                continue
            result[index + 1 : index + 1] = [side1, side2]
            added += 1
            break
    return result


def _choose_exit(rng: random.Random) -> Position:
    border = {
        (row, col)
        for row in range(GRID_SIZE)
        for col in range(GRID_SIZE)
        if row in {0, GRID_SIZE - 1} or col in {0, GRID_SIZE - 1}
    }
    candidates = [p for p in sorted(border) if p != (0, 0) and p[0] + p[1] >= 6]
    return rng.choice(candidates)


def _difficulty_counts(difficulty: str, rng: random.Random) -> tuple[int, int, int, int]:
    if difficulty == "easy":
        return rng.randint(4, 7), rng.randint(1, 2), 1, rng.randint(0, 1)
    if difficulty == "medium":
        return rng.randint(8, 12), rng.randint(3, 5), rng.randint(1, 2), rng.randint(1, 2)
    if difficulty == "hard":
        return rng.randint(12, 18), rng.randint(5, 8), rng.randint(2, 3), rng.randint(2, 4)
    raise ValueError(f"Unknown difficulty: {difficulty}")


def generate_map(
    *,
    seed: int,
    difficulty: str,
    map_id: str,
    output_path: str | Path,
) -> GeneratedMapInfo:
    rng = random.Random(seed)
    start = (0, 0)
    exit_position = _choose_exit(rng)
    interior = [(r, c) for r in range(1, GRID_SIZE - 1) for c in range(1, GRID_SIZE - 1) if (r, c) != exit_position]
    gold_position = rng.choice(interior)

    wall_count, pit_count, wumpus_count, detour_count = _difficulty_counts(difficulty, rng)
    path_to_gold = _add_detours(_random_shortest_path(start, gold_position, rng), detour_count, rng)
    path_to_exit = _add_detours(_random_shortest_path(gold_position, exit_position, rng), detour_count, rng)
    protected_path = path_to_gold + path_to_exit[1:]
    protected = set(protected_path)

    safety_buffer = set(protected)
    if difficulty == "easy":
        for position in protected:
            safety_buffer.update(_neighbors(position))
    elif difficulty == "medium":
        for index, position in enumerate(protected_path):
            if index % 3 == 0:
                safety_buffer.update(_neighbors(position))

    all_cells = {(r, c) for r in range(GRID_SIZE) for c in range(GRID_SIZE)}
    reserved = protected | {start, exit_position, gold_position}
    candidates = sorted(all_cells - reserved)

    def choose_cells(count: int, avoid: set[Position]) -> set[Position]:
        pool = [cell for cell in candidates if cell not in avoid]
        if len(pool) < count:
            raise RuntimeError("Not enough free cells for map generation.")
        return set(rng.sample(pool, count))

    occupied: set[Position] = set()
    walls = choose_cells(wall_count, occupied | safety_buffer)
    occupied.update(walls)
    hazard_buffer = safety_buffer if difficulty == "easy" else protected
    pits = choose_cells(pit_count, occupied | hazard_buffer)
    occupied.update(pits)
    wumpus = choose_cells(wumpus_count, occupied | hazard_buffer)

    grid = [["*" for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    for row, col in walls:
        grid[row][col] = "D"
    for row, col in pits:
        grid[row][col] = "P"
    for row, col in wumpus:
        grid[row][col] = "W"
    grid[gold_position[0]][gold_position[1]] = "G"

    initial_health = 120
    gold_score = 50
    pit_penalty = 10

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    content = ["".join(row) for row in grid]
    content.extend(
        [
            str(initial_health),
            str(gold_score),
            str(pit_penalty),
            f"{exit_position[0] + 1} {exit_position[1] + 1}",
        ]
    )
    output.write_text("\n".join(content) + "\n", encoding="utf-8")

    config = load_map(output)
    agent = AStarAgent(config)
    agent.reset()
    if agent.plan_result is None:
        raise RuntimeError("Generated map has no A* plan.")

    return GeneratedMapInfo(
        map_id=map_id,
        difficulty=difficulty,
        seed=seed,
        initial_health=initial_health,
        gold_score=gold_score,
        pit_penalty=pit_penalty,
        exit_position=exit_position,
        gold_position=gold_position,
        walls=len(walls),
        pits=len(pits),
        wumpus=len(wumpus),
        protected_path_length=len(protected_path) - 1,
        astar_plan_length=len(agent.plan_result.actions),
    )


def generate_suite(
    output_dir: str | Path,
    *,
    prefix: str,
    maps_per_difficulty: int,
    seed: int,
) -> list[GeneratedMapInfo]:
    if maps_per_difficulty < 1:
        raise ValueError("maps_per_difficulty must be positive.")
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    for old_map in output_dir.glob(f"{prefix}_*.txt"):
        old_map.unlink()

    rng = random.Random(seed)
    manifest: list[GeneratedMapInfo] = []
    index = 1
    for difficulty in ("easy", "medium", "hard"):
        for _ in range(maps_per_difficulty):
            map_seed = rng.randrange(1, 2**31)
            map_id = f"{prefix}_{index:03d}_{difficulty}"
            info = generate_map(
                seed=map_seed,
                difficulty=difficulty,
                map_id=map_id,
                output_path=output_dir / f"{map_id}.txt",
            )
            manifest.append(info)
            index += 1

    (output_dir / "manifest.json").write_text(
        json.dumps([asdict(item) for item in manifest], indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def generate_test_suite(
    output_dir: str | Path = "maps/test",
    *,
    maps_per_difficulty: int = 10,
    seed: int = 20260730,
) -> list[GeneratedMapInfo]:
    return generate_suite(
        output_dir,
        prefix="test",
        maps_per_difficulty=maps_per_difficulty,
        seed=seed,
    )


def generate_training_suite(
    output_dir: str | Path = "maps/training",
    *,
    maps_per_difficulty: int = 4,
    seed: int = 1701,
) -> list[GeneratedMapInfo]:
    return generate_suite(
        output_dir,
        prefix="training",
        maps_per_difficulty=maps_per_difficulty,
        seed=seed,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate deterministic Wumpus maps.")
    parser.add_argument("--output", default="maps/test")
    parser.add_argument("--prefix", default="test")
    parser.add_argument("--per-difficulty", type=int, default=10)
    parser.add_argument("--seed", type=int, default=20260730)
    args = parser.parse_args()
    manifest = generate_suite(
        args.output,
        prefix=args.prefix,
        maps_per_difficulty=args.per_difficulty,
        seed=args.seed,
    )
    print(f"Generated {len(manifest)} maps in {args.output}")


if __name__ == "__main__":
    main()
