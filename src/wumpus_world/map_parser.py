from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

ALLOWED_SYMBOLS = {"*", "D", "P", "W", "G"}
GRID_SIZE = 8
CONFIG_LINE_COUNT = 4


@dataclass(frozen=True)
class MapConfig:
    grid: tuple[tuple[str, ...], ...]
    initial_health: int
    gold_score: int
    pit_penalty: int
    exit_position: tuple[int, int]


def _parse_int_line(line: str, name: str) -> int:
    raw = line.split("=", 1)[-1].strip()
    try:
        return int(raw)
    except ValueError as exc:
        raise ValueError(f"Invalid {name}: {line!r}") from exc


def _parse_exit(line: str) -> tuple[int, int]:
    raw = line.split("=", 1)[-1].replace(",", " ").strip()
    parts = raw.split()
    if len(parts) != 2:
        raise ValueError("Exit position must contain exactly two integers.")
    try:
        row, col = map(int, parts)
    except ValueError as exc:
        raise ValueError(f"Invalid exit position: {line!r}") from exc

    row -= 1
    col -= 1
    if not (0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE):
        raise ValueError("Exit position must be inside the 8x8 grid.")
    return row, col


def load_map(path: str | Path) -> MapConfig:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Map file not found: {path}")

    lines = [line.strip() for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    expected = GRID_SIZE + CONFIG_LINE_COUNT
    if len(lines) != expected:
        raise ValueError(
            f"Map file must contain exactly {GRID_SIZE} grid rows and "
            f"{CONFIG_LINE_COUNT} configuration lines; got {len(lines)} non-empty lines."
        )

    grid_lines = lines[:GRID_SIZE]
    if any(len(row) != GRID_SIZE for row in grid_lines):
        raise ValueError("Every grid row must contain exactly 8 characters.")

    invalid = sorted({char for row in grid_lines for char in row if char not in ALLOWED_SYMBOLS})
    if invalid:
        raise ValueError(f"Invalid map symbols: {invalid}")

    initial_health = _parse_int_line(lines[8], "initial health")
    gold_score = _parse_int_line(lines[9], "gold score")
    pit_penalty = _parse_int_line(lines[10], "pit penalty")
    exit_position = _parse_exit(lines[11])

    if initial_health <= 0:
        raise ValueError("Initial health must be positive.")
    if gold_score < 0 or pit_penalty < 0:
        raise ValueError("Gold score and pit penalty cannot be negative.")

    grid = tuple(tuple(row) for row in grid_lines)
    start = (0, 0)
    if grid[start[0]][start[1]] != "*":
        raise ValueError("Start cell (1,1) must be an empty and safe cell.")
    if exit_position == start:
        raise ValueError("Exit position must be different from the start cell.")
    if grid[exit_position[0]][exit_position[1]] != "*":
        raise ValueError("Exit cell must be empty and safe.")
    if not any("G" in row for row in grid_lines):
        raise ValueError("Map must contain at least one gold cell.")

    return MapConfig(
        grid=grid,
        initial_health=initial_health,
        gold_score=gold_score,
        pit_penalty=pit_penalty,
        exit_position=exit_position,
    )
