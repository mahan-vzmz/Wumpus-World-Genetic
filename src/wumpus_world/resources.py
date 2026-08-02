from __future__ import annotations

from importlib.resources import files


def default_map_path() -> str:
    return str(files("wumpus_world").joinpath("data/maps/sample_01.txt"))


def default_weights_path() -> str:
    return str(files("wumpus_world").joinpath("data/best_weights.json"))
