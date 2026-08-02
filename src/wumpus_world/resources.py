from __future__ import annotations

from importlib.resources import files
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def default_map_path() -> str:
    root_map = ROOT / "maps" / "sample_01.txt"
    if root_map.exists():
        return str(root_map)
    return str(files("wumpus_world").joinpath("data/maps/sample_01.txt"))


def default_weights_path() -> str:
    root_weights = ROOT / "best_weights.json"
    if root_weights.exists():
        return str(root_weights)
    return str(files("wumpus_world").joinpath("data/best_weights.json"))
