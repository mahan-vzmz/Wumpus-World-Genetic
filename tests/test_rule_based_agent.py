from __future__ import annotations

from wumpus_world.agents.rule_based_agent import RuleBasedAgent
from wumpus_world.environment import Action, WumpusEnvironment
from wumpus_world.knowledge_base import KnowledgeBase
from wumpus_world.map_parser import load_map


def test_no_breeze_and_no_stench_make_neighbors_safe() -> None:
    kb = KnowledgeBase(rows=8, cols=8)
    kb.observe(
        position=(0, 0),
        breeze=False,
        stench=False,
        pit_here=False,
        valid_actions=["RIGHT", "DOWN"],
    )
    assert (0, 1) in kb.safe
    assert (1, 0) in kb.safe


def test_positive_breeze_creates_pit_candidates() -> None:
    kb = KnowledgeBase(rows=8, cols=8)
    kb.observe(
        position=(0, 0),
        breeze=True,
        stench=False,
        pit_here=False,
        valid_actions=["RIGHT", "DOWN"],
    )
    assert kb.possible_pits == {(0, 1), (1, 0)}
    assert (0, 1) not in kb.safe


def test_entered_pit_is_not_marked_safe() -> None:
    kb = KnowledgeBase(rows=8, cols=8)
    kb.observe(
        position=(1, 1),
        breeze=False,
        stench=False,
        pit_here=True,
        valid_actions=["UP", "RIGHT", "DOWN", "LEFT"],
    )
    assert (1, 1) in kb.definite_pits
    assert (1, 1) not in kb.safe
    assert kb.status((1, 1)) == "DEFINITE_PIT"


def test_constraint_reduction_can_infer_definite_pit() -> None:
    kb = KnowledgeBase(rows=8, cols=8)
    kb.observe(
        position=(0, 0),
        breeze=True,
        stench=False,
        pit_here=False,
        valid_actions=["RIGHT", "DOWN"],
    )
    kb.observe(
        position=(1, 0),
        breeze=False,
        stench=False,
        pit_here=False,
        valid_actions=["UP", "RIGHT", "DOWN"],
    )
    assert kb.definite_pits == {(0, 1)}


def test_rule_agent_prefers_safe_unvisited_neighbor() -> None:
    config = load_map("maps/sample_rule_safe.txt")
    agent = RuleBasedAgent(config)
    agent.reset()
    action = agent.choose_action(
        {
            "position": (0, 0),
            "health": 120,
            "breeze": False,
            "stench": False,
            "pit_here": False,
            "has_gold": False,
            "valid_actions": ["RIGHT", "DOWN"],
        }
    )
    assert action == Action.RIGHT
    assert agent.last_trace is not None
    assert "safe" in agent.last_trace.decision.lower()


def test_rule_agent_collects_gold_and_escapes_on_safe_map() -> None:
    config = load_map("maps/sample_rule_safe.txt")
    env = WumpusEnvironment(config)
    agent = RuleBasedAgent(config)
    observation = env.reset()
    agent.reset()
    for _ in range(200):
        action = agent.choose_action(observation)
        observation, _, done, _ = env.step(action)
        if done:
            break
    assert env.state.success is True
    assert env.state.collected_gold == 1
    assert env.state.pit_entries == 0


def test_rule_agent_uses_only_dimensions_and_exit_from_config() -> None:
    config = load_map("maps/sample_rule_reasoning.txt")
    agent = RuleBasedAgent(config)
    assert not hasattr(agent, "config")
    assert agent.rows == 8 and agent.cols == 8
    assert agent.exit_position == config.exit_position
