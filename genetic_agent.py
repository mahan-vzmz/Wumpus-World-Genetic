from __future__ import annotations
import json
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable
from base_agent import BaseAgent
from environment import ACTION_DELTAS, Action
from knowledge_base import KnowledgeBase, Position
from map_parser import MapConfig

ACTION_ORDER = (Action.RIGHT, Action.DOWN, Action.LEFT, Action.UP)
GENE_NAMES = (
    "safe_bonus",
    "unvisited_bonus",
    "exit_progress_weight",
    "pit_risk_penalty",
    "wumpus_risk_penalty",
    "unknown_weight",
    "revisit_penalty",
    "reverse_penalty",
    "frontier_bonus",
    "health_caution_penalty",
)
GENE_BOUNDS: dict[str, tuple[float, float]] = {
    "safe_bonus": (0.0, 25.0),
    "unvisited_bonus": (0.0, 25.0),
    "exit_progress_weight": (0.0, 25.0),
    "pit_risk_penalty": (-25.0, 0.0),
    "wumpus_risk_penalty": (-35.0, 0.0),
    "unknown_weight": (-12.0, 12.0),
    "revisit_penalty": (-12.0, 0.0),
    "reverse_penalty": (-12.0, 0.0),
    "frontier_bonus": (0.0, 12.0),
    "health_caution_penalty": (-20.0, 0.0),
}


@dataclass(frozen=True)
class GeneticWeights:
    safe_bonus: float = 12.0
    unvisited_bonus: float = 13.0
    exit_progress_weight: float = 12.0
    pit_risk_penalty: float = -8.0
    wumpus_risk_penalty: float = -22.0
    unknown_weight: float = -1.0
    revisit_penalty: float = -3.0
    reverse_penalty: float = -4.0
    frontier_bonus: float = 3.0
    health_caution_penalty: float = -8.0

    def as_genome(self) -> list[float]:
        return [float(getattr(self, name)) for name in GENE_NAMES]

    @classmethod
    def from_genome(cls, genome: Iterable[float]) -> "GeneticWeights":
        values = list(genome)
        if len(values) != len(GENE_NAMES):
            raise ValueError(
                f"Genome must contain {len(GENE_NAMES)} values; got {len(values)}."
            )
        return cls(**dict(zip(GENE_NAMES, map(float, values))))

    def clipped(self) -> "GeneticWeights":
        values: dict[str, float] = {}
        for name in GENE_NAMES:
            lower, upper = GENE_BOUNDS[name]
            values[name] = max(lower, min(upper, float(getattr(self, name))))
        return GeneticWeights(**values)

    def save(self, path: str | Path, metadata: dict[str, Any] | None = None) -> None:
        payload: dict[str, Any] = {
            "method": "hybrid_genetic_weighted_policy",
            "genes": asdict(self),
        }
        if metadata:
            payload["metadata"] = metadata
        output = Path(path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "GeneticWeights":
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Genetic weights file not found: {path}")
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid genetic weights JSON: {path}") from exc
        genes = payload.get("genes", payload)
        missing = [name for name in GENE_NAMES if name not in genes]
        if missing:
            raise ValueError(f"Weights file is missing genes: {missing}")
        return cls(**{name: float(genes[name]) for name in GENE_NAMES}).clipped()


@dataclass(frozen=True)
class GeneticDecisionTrace:
    position: Position
    percepts: str
    candidate_scores: tuple[str, ...]
    decision: str


class GeneticAgent(BaseAgent):
    def __init__(self, config: MapConfig, weights: GeneticWeights | None = None):
        self.rows = len(config.grid)
        self.cols = len(config.grid[0])
        self.exit_position = config.exit_position
        self.initial_health = config.initial_health
        self.weights = (weights or GeneticWeights()).clipped()
        self.kb = KnowledgeBase(self.rows, self.cols)
        self.visit_counts: dict[Position, int] = {}
        self.previous_position: Position | None = None
        self.last_trace: GeneticDecisionTrace | None = None
        self.decision_history: list[GeneticDecisionTrace] = []

    def reset(self) -> None:
        self.kb = KnowledgeBase(self.rows, self.cols)
        self.visit_counts = {}
        self.previous_position = None
        self.last_trace = None
        self.decision_history = []

    def choose_action(self, observation: dict[str, Any]) -> Action:
        position = tuple(observation["position"])
        self.visit_counts[position] = self.visit_counts.get(position, 0) + 1
        self.kb.observe(
            position=position,
            breeze=bool(observation["breeze"]),
            stench=bool(observation["stench"]),
            pit_here=bool(observation.get("pit_here", False)),
            valid_actions=observation["valid_actions"],
        )

        valid_actions = [
            action
            for action in ACTION_ORDER
            if action.value in observation["valid_actions"]
        ]
        if not valid_actions:
            raise RuntimeError("No valid movement is available.")

        has_gold = bool(observation["has_gold"])
        if has_gold:
            path = self._shortest_known_safe_path(position, self.exit_position)
            if path and len(path) > 1:
                action = self._action_between(position, path[1])
                return self._record(
                    position,
                    observation,
                    (f"safe path to exit: {self._format_path(path)}",),
                    action,
                    "Gold collected; follow the shortest known-safe route to exit.",
                )

        scored: list[tuple[float, int, Action, dict[str, float]]] = []
        for order_index, action in enumerate(ACTION_ORDER):
            if action not in valid_actions:
                continue
            target = self._target(position, action)
            if target == self.exit_position and not has_gold:
                scored.append(
                    (-1_000_000.0, order_index, action, {"premature_exit": 1.0})
                )
                continue
            features = self._features(
                current=position,
                target=target,
                health=int(observation["health"]),
                has_gold=has_gold,
            )
            scored.append((self._weighted_score(features), order_index, action, features))

        if not scored:
            raise RuntimeError("All locally valid actions were rejected.")
        score, _, action, _ = max(scored, key=lambda item: (item[0], -item[1]))
        candidate_lines = tuple(
            self._format_candidate(candidate_action, candidate_score, features)
            for candidate_score, _, candidate_action, features in sorted(
                scored, key=lambda item: item[1]
            )
        )
        return self._record(
            position,
            observation,
            candidate_lines,
            action,
            f"Choose the highest weighted score ({score:.2f}).",
        )

    def _features(
        self,
        *,
        current: Position,
        target: Position,
        health: int,
        has_gold: bool,
    ) -> dict[str, float]:
        status = self.kb.status(target)
        safe = 1.0 if target in self.kb.safe else 0.0
        unvisited = 1.0 if self.visit_counts.get(target, 0) == 0 else 0.0
        revisit_count = float(self.visit_counts.get(target, 0))
        reverse = 1.0 if target == self.previous_position else 0.0
        unknown = 1.0 if status in {
            "UNKNOWN",
            "POSSIBLE_PIT",
            "POSSIBLE_WUMPUS",
            "POSSIBLE_WUMPUS_OR_PIT",
        } else 0.0

        pit_evidence = float(self.kb.evidence_pit.get(target, 0))
        if target in self.kb.definite_pits:
            pit_evidence += 5.0
        wumpus_evidence = float(self.kb.evidence_wumpus.get(target, 0))
        if target in self.kb.definite_wumpus:
            wumpus_evidence += 12.0

        exit_progress = 0.0
        if has_gold:
            exit_progress = float(
                self._manhattan(current, self.exit_position)
                - self._manhattan(target, self.exit_position)
            )

        frontier = sum(
            1
            for neighbor in self.kb.neighbors(target)
            if neighbor not in self.kb.visited and neighbor not in self.kb.walls
        ) / 4.0
        uncertainty = pit_evidence + 2.0 * wumpus_evidence + unknown
        health_ratio = max(0.0, min(1.0, health / max(1, self.initial_health)))
        low_health_risk = (1.0 - health_ratio) * uncertainty

        return {
            "safe_bonus": safe,
            "unvisited_bonus": unvisited,
            "exit_progress_weight": exit_progress,
            "pit_risk_penalty": pit_evidence,
            "wumpus_risk_penalty": wumpus_evidence,
            "unknown_weight": unknown,
            "revisit_penalty": revisit_count,
            "reverse_penalty": reverse,
            "frontier_bonus": float(frontier),
            "health_caution_penalty": low_health_risk,
        }

    def _weighted_score(self, features: dict[str, float]) -> float:
        return sum(
            float(getattr(self.weights, name)) * float(features[name])
            for name in GENE_NAMES
        )

    def _shortest_known_safe_path(
        self, start: Position, goal: Position
    ) -> list[Position] | None:
        if start == goal:
            return [start]
        allowed = set(self.kb.safe) | {start}
        allowed.add(goal)
        queue: deque[Position] = deque([start])
        parent: dict[Position, Position | None] = {start: None}
        while queue:
            current = queue.popleft()
            if current == goal:
                path: list[Position] = []
                cursor: Position | None = current
                while cursor is not None:
                    path.append(cursor)
                    cursor = parent[cursor]
                return list(reversed(path))
            for action in ACTION_ORDER:
                nxt = self._target(current, action)
                if not self._inside(nxt) or nxt in parent:
                    continue
                if nxt not in allowed:
                    continue
                if nxt == goal and current not in self.kb.safe and current != start:
                    continue
                parent[nxt] = current
                queue.append(nxt)
        return None

    def _record(
        self,
        position: Position,
        observation: dict[str, Any],
        candidate_scores: tuple[str, ...],
        action: Action,
        reason: str,
    ) -> Action:
        trace = GeneticDecisionTrace(
            position=position,
            percepts=(
                f"breeze={bool(observation['breeze'])}, "
                f"stench={bool(observation['stench'])}, "
                f"pit_here={bool(observation.get('pit_here', False))}, "
                f"health={int(observation['health'])}, "
                f"has_gold={bool(observation['has_gold'])}"
            ),
            candidate_scores=candidate_scores,
            decision=f"{action.value}: {reason}",
        )
        self.last_trace = trace
        self.decision_history.append(trace)
        self.previous_position = position
        return action

    @staticmethod
    def _format_candidate(
        action: Action, score: float, features: dict[str, float]
    ) -> str:
        if "premature_exit" in features:
            return f"{action.value}: score=-1000000.00 (premature exit without gold)"
        compact = ", ".join(
            f"{name}={value:.2f}" for name, value in features.items() if value != 0
        )
        return f"{action.value}: score={score:.2f} [{compact or 'all-zero features'}]"

    def _target(self, position: Position, action: Action) -> Position:
        dr, dc = ACTION_DELTAS[action]
        return position[0] + dr, position[1] + dc

    def _inside(self, position: Position) -> bool:
        return 0 <= position[0] < self.rows and 0 <= position[1] < self.cols

    @staticmethod
    def _action_between(start: Position, end: Position) -> Action:
        delta = (end[0] - start[0], end[1] - start[1])
        for action, action_delta in ACTION_DELTAS.items():
            if action_delta == delta:
                return action
        raise ValueError(f"Positions are not adjacent: {start} -> {end}")

    @staticmethod
    def _manhattan(a: Position, b: Position) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def _format_path(path: list[Position]) -> str:
        return " -> ".join(f"({r + 1},{c + 1})" for r, c in path)
