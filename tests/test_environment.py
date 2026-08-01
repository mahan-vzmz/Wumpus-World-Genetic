from __future__ import annotations

from pathlib import Path

import pytest

from wumpus_world.environment import Action, WumpusEnvironment
from wumpus_world.map_parser import MapConfig, load_map


def make_config(
    grid_rows: list[str],
    *,
    health: int = 100,
    exit_position: tuple[int, int] = (7, 7),
) -> MapConfig:
    return MapConfig(
        grid=tuple(tuple(row) for row in grid_rows),
        initial_health=health,
        gold_score=50,
        pit_penalty=10,
        exit_position=exit_position,
    )


def empty_grid(gold: tuple[int, int] = (3, 3)) -> list[str]:
    grid = [["*" for _ in range(8)] for _ in range(8)]
    grid[gold[0]][gold[1]] = "G"
    return ["".join(row) for row in grid]


def test_sample_map_loads() -> None:
    path = Path(__file__).parents[1] / "maps" / "sample_01.txt"
    config = load_map(path)
    assert len(config.grid) == 8
    assert config.initial_health == 120


def test_wall_blocks_but_costs_health() -> None:
    grid = empty_grid()
    grid[0] = "*D******"
    env = WumpusEnvironment(make_config(grid))
    _, _, _, info = env.step(Action.RIGHT)
    assert env.state.position == (0, 0)
    assert env.state.health == 99
    assert info["blocked"] is True


@pytest.mark.parametrize(
    ("start", "action"),
    [
        ((0, 0), Action.UP),
        ((0, 0), Action.LEFT),
        ((7, 0), Action.DOWN),
        ((0, 7), Action.RIGHT),
    ],
)
def test_all_grid_boundaries_are_blocked(start: tuple[int, int], action: Action) -> None:
    env = WumpusEnvironment(make_config(empty_grid()))
    env.state.position = start
    env.state.visited.add(start)
    health = env.state.health
    _, _, _, info = env.step(action)
    assert env.state.position == start
    assert env.state.health == health - 1
    assert info["blocked"] is True


def test_breeze_and_stench_are_generated() -> None:
    grid = empty_grid()
    grid[1] = "PW******"
    env = WumpusEnvironment(make_config(grid))
    observation = env.observe()
    assert observation["breeze"] is True
    assert observation["stench"] is False
    env.step(Action.RIGHT)
    assert env.observe()["stench"] is True


def test_pit_halves_health_after_move_cost_and_is_observed() -> None:
    grid = empty_grid()
    grid[0] = "*P******"
    env = WumpusEnvironment(make_config(grid))
    observation, _, _, _ = env.step(Action.RIGHT)
    assert env.state.health == 49
    assert env.state.pit_entries == 1
    assert observation["pit_here"] is True


def test_wumpus_ends_game() -> None:
    grid = empty_grid()
    grid[0] = "*W******"
    env = WumpusEnvironment(make_config(grid))
    _, _, done, info = env.step(Action.RIGHT)
    assert done is True
    assert env.state.health == 0
    assert info["termination_reason"] == "wumpus"


def test_gold_then_exit_is_success() -> None:
    grid = empty_grid(gold=(0, 1))
    env = WumpusEnvironment(make_config(grid, exit_position=(0, 2)))
    env.step(Action.RIGHT)
    _, _, done, info = env.step(Action.RIGHT)
    assert done is True
    assert info["success"] is True
    assert env.state.collected_gold == 1
    assert info["termination_reason"] == "escaped_with_gold"


def test_exit_without_gold_is_failure() -> None:
    env = WumpusEnvironment(make_config(empty_grid(), exit_position=(0, 1)))
    _, _, done, info = env.step(Action.RIGHT)
    assert done is True
    assert info["success"] is False
    assert info["termination_reason"] == "escaped_without_gold"


def test_unknown_action_is_rejected() -> None:
    env = WumpusEnvironment(make_config(empty_grid()))
    with pytest.raises(ValueError, match="Unknown action"):
        env.step("JUMP")


def test_step_after_episode_is_rejected() -> None:
    env = WumpusEnvironment(make_config(empty_grid(), exit_position=(0, 1)))
    env.step(Action.RIGHT)
    with pytest.raises(RuntimeError, match="Episode is finished"):
        env.step(Action.LEFT)


def test_explicit_timeout_termination() -> None:
    env = WumpusEnvironment(make_config(empty_grid()))
    env.terminate("max_steps")
    assert env.state.done is True
    assert env.state.success is False
    assert env.state.termination_reason == "max_steps"
