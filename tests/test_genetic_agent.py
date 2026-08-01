from __future__ import annotations
import json
from pathlib import Path
import pytest
from wumpus_world.environment import Action, WumpusEnvironment
from wumpus_world.agents.genetic_agent import GENE_BOUNDS, GENE_NAMES, GeneticAgent, GeneticWeights
from wumpus_world.training.genetic_algorithm import GeneticTrainer, evaluate_episode
from wumpus_world.map_parser import load_map


def test_genetic_weights_round_trip(tmp_path: Path) -> None:
    original = GeneticWeights(
        safe_bonus=12.0,
        unvisited_bonus=11.0,
        exit_progress_weight=9.0,
        pit_risk_penalty=-5.0,
        wumpus_risk_penalty=-14.0,
        unknown_weight=2.0,
        revisit_penalty=-2.0,
        reverse_penalty=-3.0,
        frontier_bonus=4.0,
        health_caution_penalty=-6.0,
    )
    path = tmp_path / "weights.json"
    original.save(path, metadata={"test": True})
    loaded = GeneticWeights.load(path)
    assert loaded == original
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert payload["metadata"]["test"] is True


def test_missing_weights_file_is_explicit_error(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="not found"):
        GeneticWeights.load(tmp_path / "missing.json")


def test_genetic_agent_returns_valid_action_from_local_observation() -> None:
    config = load_map("maps/sample_rule_safe.txt")
    env = WumpusEnvironment(config)
    agent = GeneticAgent(config, GeneticWeights())
    observation = env.reset()
    agent.reset()
    action = agent.choose_action(observation)
    assert action in {Action.RIGHT, Action.DOWN}
    assert action.value in observation["valid_actions"]
    assert agent.last_trace is not None


def test_saved_genetic_weights_solve_main_sample() -> None:
    config = load_map("maps/sample_01.txt")
    weights = GeneticWeights.load("best_weights.json")
    result = evaluate_episode(config, weights, max_steps=250)
    assert result.success is True
    assert result.termination_reason == "escaped_with_gold"


def test_small_genetic_training_returns_bounded_genome() -> None:
    configs = [
        load_map("maps/training/training_001_easy.txt"),
        load_map("maps/training/training_005_medium.txt"),
    ]
    trainer = GeneticTrainer(
        configs,
        population_size=6,
        generations=2,
        elite_count=1,
        tournament_size=2,
        max_steps=100,
        seed=3,
        patience=None,
    )
    result = trainer.train(verbose=False)
    genome = result.best_weights.as_genome()
    assert len(result.history) == 2
    assert len(genome) == len(GENE_NAMES)
    assert result.best_fitness == result.best_fitness
    for name, value in zip(GENE_NAMES, genome):
        lower, upper = GENE_BOUNDS[name]
        assert lower <= value <= upper
