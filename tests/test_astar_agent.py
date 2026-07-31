from __future__ import annotations
import pytest
from astar_agent import AStarAgent, NoPathError
from environment import Action, WumpusEnvironment
from map_parser import MapConfig


def make_config(
    grid_rows: list[str],
    *,
    health: int = 100,
    exit_position: tuple[int, int] = (7, 7),
    pit_penalty: int = 10,
) -> MapConfig:
    return MapConfig(
        grid=tuple(tuple(row) for row in grid_rows),
        initial_health=health,
        gold_score=50,
        pit_penalty=pit_penalty,
        exit_position=exit_position,
    )


def execute(config: MapConfig) -> tuple[WumpusEnvironment, AStarAgent]:
    env = WumpusEnvironment(config)
    agent = AStarAgent(config)
    observation = env.reset()
    agent.reset()
    for _ in range(200):
        action = agent.choose_action(observation)
        observation, _, done, _ = env.step(action)
        if done:
            return env, agent
    raise AssertionError("Agent did not finish within 200 steps.")


def test_astar_requires_reset() -> None:
    config = make_config(
        ["*G******"] + ["********" for _ in range(7)],
        exit_position=(0, 2),
    )
    agent = AStarAgent(config)
    with pytest.raises(RuntimeError, match="reset"):
        agent.choose_action({"position": (0, 0)})


def test_astar_collects_gold_then_exits() -> None:
    config = make_config(
        ["*G******"] + ["********" for _ in range(7)],
        exit_position=(0, 2),
    )
    env, agent = execute(config)
    assert env.state.success is True
    assert agent.plan_result is not None
    assert agent.plan_result.actions == (Action.RIGHT, Action.RIGHT)
    assert agent.plan_result.final_health == 98


def test_astar_routes_around_wall_and_wumpus() -> None:
    config = make_config(
        ["*DWG****"] + ["********" for _ in range(7)],
        exit_position=(0, 4),
    )
    env, agent = execute(config)
    assert env.state.success is True
    assert agent.plan_result is not None
    assert all(config.grid[r][c] not in {"D", "W"} for r, c in agent.plan_result.path)


def test_astar_prefers_safe_detour_over_short_pit_route() -> None:
    config = make_config(
        ["*PG*****"] + ["********" for _ in range(7)],
        exit_position=(0, 3),
        pit_penalty=10,
    )
    env, agent = execute(config)
    assert env.state.success is True
    assert env.state.pit_entries == 0
    assert agent.plan_result is not None
    assert (0, 1) not in agent.plan_result.path


def test_astar_chooses_reachable_gold() -> None:
    config = make_config(
        [
            "*DGD****",
            "*D*D****",
            "*D*D****",
            "*D*D****",
            "*D*D****",
            "*D*D****",
            "*D*D****",
            "***G****",
        ],
        exit_position=(7, 4),
    )
    env, agent = execute(config)
    assert env.state.success is True
    assert agent.plan_result is not None
    assert (7, 3) in agent.plan_result.path
    assert (0, 2) not in agent.plan_result.path


def test_astar_reports_no_survivable_path() -> None:
    config = make_config(
        [
            "*D******",
            "DGD*****",
            "*D******",
            "********",
            "********",
            "********",
            "********",
            "********",
        ],
        health=20,
        exit_position=(7, 7),
    )
    agent = AStarAgent(config)
    with pytest.raises(NoPathError):
        agent.reset()
