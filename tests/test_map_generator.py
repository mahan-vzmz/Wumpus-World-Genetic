from __future__ import annotations

import json
from pathlib import Path

from astar_agent import AStarAgent
from map_generator import generate_map, generate_test_suite
from map_parser import load_map


def test_generated_map_is_valid_and_solvable(tmp_path: Path) -> None:
    path = tmp_path / "one.txt"
    info = generate_map(seed=123, difficulty="medium", map_id="one", output_path=path)
    config = load_map(path)
    agent = AStarAgent(config)
    agent.reset()
    assert info.gold_position
    assert agent.plan_result is not None
    assert agent.plan_result.final_health > 0


def test_generation_is_reproducible(tmp_path: Path) -> None:
    first = tmp_path / "first.txt"
    second = tmp_path / "second.txt"
    generate_map(seed=99, difficulty="hard", map_id="a", output_path=first)
    generate_map(seed=99, difficulty="hard", map_id="b", output_path=second)
    assert first.read_text(encoding="utf-8") == second.read_text(encoding="utf-8")


def test_suite_contains_three_difficulties_and_manifest(tmp_path: Path) -> None:
    manifest = generate_test_suite(tmp_path, maps_per_difficulty=2, seed=8)
    assert len(manifest) == 6
    assert {item.difficulty for item in manifest} == {"easy", "medium", "hard"}
    assert len(list(tmp_path.glob("test_*.txt"))) == 6
    payload = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert len(payload) == 6


def test_generated_suite_has_equal_initial_health_and_varied_exits(tmp_path: Path) -> None:
    manifest = generate_test_suite(tmp_path, maps_per_difficulty=4, seed=2026)
    assert {item.initial_health for item in manifest} == {120}
    assert len({item.exit_position for item in manifest}) > 1
    assert len({item.astar_plan_length for item in manifest}) > 1
