from __future__ import annotations

from typing import Any

from wumpus_world.agents.astar_agent import AStarAgent, NoPathError
from wumpus_world.agents.base_agent import BaseAgent
from wumpus_world.agents.genetic_agent import GeneticAgent, GeneticWeights
from wumpus_world.agents.random_agent import RandomAgent
from wumpus_world.agents.rule_based_agent import RuleBasedAgent
from wumpus_world.environment import WumpusEnvironment
from wumpus_world.map_parser import load_map


def build_agent(
    name: str,
    env: WumpusEnvironment,
    *,
    weights_path: str = "best_weights.json",
    use_default_weights: bool = False,
) -> BaseAgent:
    if name == "astar":
        return AStarAgent(env.config)
    if name == "rule":
        return RuleBasedAgent(env.config)
    if name == "genetic":
        weights = GeneticWeights() if use_default_weights else GeneticWeights.load(weights_path)
        return GeneticAgent(env.config, weights)
    if name == "random":
        return RandomAgent(seed=7)
    raise ValueError(f"Unknown agent: {name}")


def _print_rule_trace(agent: RuleBasedAgent) -> None:
    trace = agent.last_trace
    if trace is None:
        return
    print("Rule-based reasoning")
    print(f"  percepts: {trace.percepts}")
    if trace.inferences:
        print("  inferences:")
        for item in trace.inferences:
            print(f"    - {item}")
    if trace.candidates:
        print("  candidates:")
        for item in trace.candidates:
            print(f"    - {item}")
    print(f"  decision: {trace.decision}")


def _print_genetic_trace(agent: GeneticAgent) -> None:
    trace = agent.last_trace
    if trace is None:
        return
    print("Hybrid genetic weighted decision")
    print(f"  percepts: {trace.percepts}")
    if trace.candidate_scores:
        print("  candidate scores:")
        for item in trace.candidate_scores:
            print(f"    - {item}")
    print(f"  decision: {trace.decision}")


def run_episode(
    map_path: str,
    agent_name: str = "astar",
    max_steps: int = 250,
    *,
    weights_path: str = "best_weights.json",
    use_default_weights: bool = False,
    verbose: bool = True,
) -> dict[str, Any]:
    if max_steps < 1:
        raise ValueError("max_steps must be positive.")

    try:
        env = WumpusEnvironment(load_map(map_path))
        agent = build_agent(
            agent_name,
            env,
            weights_path=weights_path,
            use_default_weights=use_default_weights,
        )
        observation = env.reset()
        agent.reset()
    except (NoPathError, FileNotFoundError, ValueError) as exc:
        env_bound = "env" in locals()
        result = {
            "agent": agent_name,
            "success": False,
            "termination_reason": "initialization_error",
            "error": f"{type(exc).__name__}: {exc}",
            "initial_health": env.config.initial_health if env_bound else 0,
            "remaining_health": env.state.health if env_bound else 0,
            "score": env.state.score if env_bound else 0,
            "score_delta": (env.state.score - env.config.initial_health) if env_bound else 0,
            "steps": env.state.steps if env_bound else 0,
            "pit_entries": env.state.pit_entries if env_bound else 0,
            "collected_gold": env.state.collected_gold if env_bound else 0,
        }
        if verbose:
            print("Initialization failed:", result["error"])
        return result

    if verbose:
        print(f"Agent: {agent_name}")
        if isinstance(agent, AStarAgent) and agent.plan_result is not None:
            plan = agent.plan_result
            print("A* planned actions:", " -> ".join(a.value for a in plan.actions))
            print(
                "A* plan summary: "
                f"steps={len(plan.actions)} cost={plan.total_cost} "
                f"predicted_health={plan.final_health} expanded={plan.expanded_nodes}"
            )
        if isinstance(agent, GeneticAgent):
            print("Loaded evolved genetic weights:")
            for name, value in zip(agent.weights.__dataclass_fields__, agent.weights.as_genome()):
                print(f"  {name}={value:.4f}")
        print("Initial state")
        print(env.render())
        print()

    for _ in range(max_steps):
        try:
            action = agent.choose_action(observation)
        except RuntimeError as exc:
            env.terminate("agent_stopped")
            error = str(exc)
            break

        if verbose and isinstance(agent, RuleBasedAgent):
            _print_rule_trace(agent)
        if verbose and isinstance(agent, GeneticAgent):
            _print_genetic_trace(agent)

        observation, reward, done, _ = env.step(action)
        if verbose:
            print(f"action={action.value} reward={reward}")
            print(env.render())
            print(
                f"breeze={observation['breeze']} stench={observation['stench']} "
                f"pit_here={observation['pit_here']} done={done} "
                f"reason={env.state.termination_reason}"
            )
            print("-" * 40)
        if done:
            break
    else:
        error = "Maximum step limit reached."

    if not env.state.done:
        env.terminate("max_steps")

    result: dict[str, Any] = {
        "agent": agent_name,
        "success": env.state.success,
        "termination_reason": env.state.termination_reason,
        "initial_health": env.config.initial_health,
        "remaining_health": env.state.health,
        "score": env.state.score,
        "score_delta": env.state.score - env.config.initial_health,
        "steps": env.state.steps,
        "pit_entries": env.state.pit_entries,
        "collected_gold": env.state.collected_gold,
    }
    if "error" in locals():
        result["error"] = error
    if isinstance(agent, AStarAgent) and agent.plan_result is not None:
        result["expanded_nodes"] = agent.plan_result.expanded_nodes
        result["plan_cost"] = agent.plan_result.total_cost
        result["planned_steps"] = len(agent.plan_result.actions)
    if isinstance(agent, RuleBasedAgent):
        result["known_safe_cells"] = len(agent.kb.safe)
        result["visited_cells"] = len(agent.kb.visited)
        result["knowledge"] = agent.kb.snapshot()
    if isinstance(agent, GeneticAgent):
        result["known_safe_cells"] = len(agent.kb.safe)
        result["visited_cells"] = len(agent.kb.visited)
        result["weights"] = {name: getattr(agent.weights, name) for name in agent.weights.__dataclass_fields__}
    if verbose:
        print("Final result:", result)
    return result
