from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Any, Callable, Iterable

from base_agent import BaseAgent
from environment import ACTION_DELTAS, Action
from knowledge_base import KnowledgeBase, Position
from map_parser import MapConfig

ACTION_ORDER = (Action.RIGHT, Action.DOWN, Action.LEFT, Action.UP)


@dataclass(frozen=True)
class DecisionTrace:
    position: Position
    percepts: str
    inferences: tuple[str, ...]
    candidates: tuple[str, ...]
    decision: str


class RuleBasedAgent(BaseAgent):
    """Online knowledge-based agent using local percepts and safe backtracking."""

    def __init__(self, config: MapConfig):
        self.rows = len(config.grid)
        self.cols = len(config.grid[0])
        self.exit_position = config.exit_position
        self.kb = KnowledgeBase(self.rows, self.cols)
        self.decision_history: list[DecisionTrace] = []
        self.last_trace: DecisionTrace | None = None
        self._has_gold = False

    def reset(self) -> None:
        self.kb = KnowledgeBase(self.rows, self.cols)
        self.decision_history = []
        self.last_trace = None
        self._has_gold = False

    def choose_action(self, observation: dict[str, Any]) -> Action:
        position = tuple(observation["position"])
        self._has_gold = bool(observation["has_gold"])
        inferences = self.kb.observe(
            position=position,
            breeze=bool(observation["breeze"]),
            stench=bool(observation["stench"]),
            pit_here=bool(observation.get("pit_here", False)),
            valid_actions=observation["valid_actions"],
        )

        valid_actions = {Action(action) for action in observation["valid_actions"]}
        if not valid_actions:
            raise RuntimeError("No locally valid movement is available.")

        # 1) After collecting gold, follow the shortest known-safe route to exit.
        if self._has_gold:
            path = self._shortest_safe_path(position, self.exit_position)
            if path and len(path) > 1:
                action = self._action_between(position, path[1])
                return self._record(
                    position,
                    observation,
                    inferences,
                    [f"safe path to exit: {self._format_path(path)}"],
                    action,
                    "Gold is collected; follow the known-safe shortest path to exit.",
                )
            if self.exit_position in self._adjacent_positions(position, valid_actions):
                action = self._action_between(position, self.exit_position)
                return self._record(
                    position,
                    observation,
                    inferences,
                    ["exit is adjacent"],
                    action,
                    "Gold is collected; enter the adjacent exit.",
                )

        # 2) Prefer a nearest provably safe, unvisited cell.
        safe_targets = {
            p
            for p in self.kb.safe
            if p not in self.kb.visited
            and (self._has_gold or p != self.exit_position)
        }
        safe_path = self._shortest_path_to_any(position, safe_targets, self.kb.safe)
        if safe_path and len(safe_path) > 1:
            action = self._action_between(position, safe_path[1])
            return self._record(
                position,
                observation,
                inferences,
                [f"nearest safe frontier: {self._format_path(safe_path)}"],
                action,
                "Move toward the nearest safe unvisited cell, using safe backtracking.",
            )

        # 3) If no safe frontier remains, approach the least-risk unknown cell.
        frontier_choice = self._least_risky_frontier(position)
        if frontier_choice is not None:
            target, approach_path, risk = frontier_choice
            if len(approach_path) > 1:
                action = self._action_between(position, approach_path[1])
                reason = (
                    f"No safe frontier remains; backtrack toward least-risk target "
                    f"{self._fmt(target)} (risk={risk:.1f})."
                )
            else:
                action = self._action_between(position, target)
                reason = (
                    f"No safe move remains; enter least-risk frontier "
                    f"{self._fmt(target)} (risk={risk:.1f})."
                )
            candidates = [
                f"{self._fmt(p)} risk={self.kb.risk(p):.1f} status={self.kb.status(p)}"
                for p in self._frontier_cells()
                if self.kb.risk(p) != float("inf")
            ]
            return self._record(
                position,
                observation,
                inferences,
                candidates,
                action,
                reason,
            )

        # 4) Last resort: choose the locally valid move with lowest known risk.
        action = self._fallback_action(position, valid_actions)
        return self._record(
            position,
            observation,
            inferences,
            [f"valid local actions: {', '.join(sorted(a.value for a in valid_actions))}"],
            action,
            "No reachable frontier remains; use the safest valid local fallback.",
        )

    def _least_risky_frontier(
        self, current: Position
    ) -> tuple[Position, list[Position], float] | None:
        best: tuple[tuple[float, int, int, int], Position, list[Position]] | None = None
        for target in self._frontier_cells():
            if target in self.kb.walls or target in self.kb.definite_wumpus:
                continue
            if not self._has_gold and target == self.exit_position:
                continue
            risk = self.kb.risk(target)
            if risk == float("inf"):
                continue

            adjacent_safe = [p for p in self.kb.neighbors(target) if p in self.kb.safe]
            if current in self.kb.neighbors(target):
                adjacent_safe.append(current)
            for approach in adjacent_safe:
                path = self._shortest_safe_path(current, approach)
                if not path:
                    continue
                key = (risk, len(path), target[0], target[1])
                if best is None or key < best[0]:
                    best = (key, target, path)
        if best is None:
            return None
        key, target, path = best
        return target, path, key[0]

    def _frontier_cells(self) -> list[Position]:
        frontier: set[Position] = set()
        roots = self.kb.safe | self.kb.visited
        for root in roots:
            for neighbor in self.kb.neighbors(root):
                if neighbor in self.kb.visited or neighbor in self.kb.walls:
                    continue
                frontier.add(neighbor)
        return sorted(frontier)

    def _shortest_safe_path(
        self, start: Position, goal: Position
    ) -> list[Position] | None:
        if start == goal:
            return [start]
        allowed = set(self.kb.safe)
        allowed.add(start)
        if goal not in allowed:
            return None
        return self._bfs(start, lambda p: p == goal, allowed)

    def _shortest_path_to_any(
        self,
        start: Position,
        goals: set[Position],
        allowed: Iterable[Position],
    ) -> list[Position] | None:
        if not goals:
            return None
        allowed_set = set(allowed)
        allowed_set.add(start)
        return self._bfs(start, lambda p: p in goals, allowed_set)

    def _bfs(
        self,
        start: Position,
        is_goal: Callable[[Position], bool],
        allowed: set[Position],
    ) -> list[Position] | None:
        queue: deque[Position] = deque([start])
        parent: dict[Position, Position | None] = {start: None}
        while queue:
            current = queue.popleft()
            if is_goal(current):
                path: list[Position] = []
                cursor: Position | None = current
                while cursor is not None:
                    path.append(cursor)
                    cursor = parent[cursor]
                return list(reversed(path))
            for action in ACTION_ORDER:
                dr, dc = ACTION_DELTAS[action]
                nxt = (current[0] + dr, current[1] + dc)
                if nxt in allowed and nxt not in parent:
                    parent[nxt] = current
                    queue.append(nxt)
        return None

    def _fallback_action(self, position: Position, valid_actions: set[Action]) -> Action:
        ranked: list[tuple[float, int, Action]] = []
        for index, action in enumerate(ACTION_ORDER):
            if action not in valid_actions:
                continue
            dr, dc = ACTION_DELTAS[action]
            target = (position[0] + dr, position[1] + dc)
            ranked.append((self.kb.risk(target), index, action))
        if not ranked:
            raise RuntimeError("No valid fallback action exists.")
        return min(ranked)[2]

    def _adjacent_positions(
        self, position: Position, valid_actions: set[Action]
    ) -> set[Position]:
        result: set[Position] = set()
        for action in valid_actions:
            dr, dc = ACTION_DELTAS[action]
            result.add((position[0] + dr, position[1] + dc))
        return result

    @staticmethod
    def _action_between(start: Position, end: Position) -> Action:
        delta = (end[0] - start[0], end[1] - start[1])
        for action, action_delta in ACTION_DELTAS.items():
            if action_delta == delta:
                return action
        raise ValueError(f"Positions are not orthogonally adjacent: {start} -> {end}")

    def _record(
        self,
        position: Position,
        observation: dict[str, Any],
        inferences: list[str],
        candidates: list[str],
        action: Action,
        reason: str,
    ) -> Action:
        trace = DecisionTrace(
            position=position,
            percepts=(
                f"breeze={bool(observation['breeze'])}, "
                f"stench={bool(observation['stench'])}, "
                f"pit_here={bool(observation.get('pit_here', False))}, "
                f"has_gold={bool(observation['has_gold'])}"
            ),
            inferences=tuple(inferences),
            candidates=tuple(candidates),
            decision=f"{action.value}: {reason}",
        )
        self.last_trace = trace
        self.decision_history.append(trace)
        return action

    @staticmethod
    def _format_path(path: list[Position]) -> str:
        return " -> ".join(RuleBasedAgent._fmt(p) for p in path)

    @staticmethod
    def _fmt(position: Position) -> str:
        return f"({position[0] + 1},{position[1] + 1})"
