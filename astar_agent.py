from __future__ import annotations

from dataclasses import dataclass
from heapq import heappop, heappush
from itertools import count
from math import inf
from typing import Any

from base_agent import BaseAgent
from environment import ACTION_DELTAS, Action
from map_parser import MapConfig


@dataclass(frozen=True)
class SearchState:
    position: tuple[int, int]
    health: int
    has_gold: bool


@dataclass(frozen=True)
class PlanResult:
    actions: tuple[Action, ...]
    path: tuple[tuple[int, int], ...]
    total_cost: int
    final_health: int
    expanded_nodes: int


class NoPathError(RuntimeError):
    """Raised when no survivable route can collect gold and reach the exit."""


class AStarAgent(BaseAgent):
    """Full-information, risk-aware A* baseline."""

    def __init__(self, config: MapConfig):
        self.config = config
        self.rows = len(config.grid)
        self.cols = len(config.grid[0])
        self.gold_positions = {
            (r, c)
            for r, row in enumerate(config.grid)
            for c, cell in enumerate(row)
            if cell == "G"
        }
        self.plan_result: PlanResult | None = None
        self._next_action_index = 0
        self._expected_positions: tuple[tuple[int, int], ...] = ()

    def reset(self) -> None:
        self.plan_result = self.plan(
            start=(0, 0),
            initial_health=self.config.initial_health,
            has_gold=False,
        )
        self._next_action_index = 0
        self._expected_positions = self.plan_result.path

    def choose_action(self, observation: dict[str, Any]) -> Action:
        if self.plan_result is None:
            raise RuntimeError("A* agent must be reset before use.")
        if self._next_action_index >= len(self.plan_result.actions):
            raise RuntimeError("A* plan is finished; no action remains.")

        current_position = tuple(observation["position"])
        expected = self._expected_positions[self._next_action_index]
        if current_position != expected:
            self.plan_result = self.plan(
                start=current_position,
                initial_health=int(observation["health"]),
                has_gold=bool(observation["has_gold"]),
            )
            self._next_action_index = 0
            self._expected_positions = self.plan_result.path

        action = self.plan_result.actions[self._next_action_index]
        self._next_action_index += 1
        return action

    def plan(
        self,
        *,
        start: tuple[int, int],
        initial_health: int,
        has_gold: bool,
    ) -> PlanResult:
        if initial_health <= 0:
            raise NoPathError("Initial health must be positive.")

        start_state = SearchState(start, initial_health, has_gold)
        frontier: list[tuple[int, int, int, SearchState]] = []
        tie_breaker = count()
        heappush(frontier, (self._heuristic(start_state), 0, next(tie_breaker), start_state))
        best_cost: dict[SearchState, int] = {start_state: 0}
        came_from: dict[SearchState, tuple[SearchState, Action]] = {}
        expanded_nodes = 0

        while frontier:
            _, current_cost, _, current = heappop(frontier)
            if current_cost != best_cost.get(current):
                continue

            expanded_nodes += 1
            if current.has_gold and current.position == self.config.exit_position:
                actions, path = self._reconstruct(came_from, current)
                return PlanResult(
                    actions=actions,
                    path=path,
                    total_cost=current_cost,
                    final_health=current.health,
                    expanded_nodes=expanded_nodes,
                )

            for action, next_state, transition_cost in self._successors(current):
                new_cost = current_cost + transition_cost
                if new_cost >= best_cost.get(next_state, inf):
                    continue
                best_cost[next_state] = new_cost
                came_from[next_state] = (current, action)
                priority = new_cost + self._heuristic(next_state)
                heappush(
                    frontier,
                    (priority, new_cost, next(tie_breaker), next_state),
                )

        raise NoPathError("No survivable path can collect gold and reach the exit.")

    def _successors(
        self, state: SearchState
    ) -> list[tuple[Action, SearchState, int]]:
        successors: list[tuple[Action, SearchState, int]] = []
        row, col = state.position
        for action, (dr, dc) in ACTION_DELTAS.items():
            next_position = (row + dr, col + dc)
            if not self._inside(next_position):
                continue
            cell = self._cell_at(next_position)
            if cell in {"D", "W"}:
                continue
            if next_position == self.config.exit_position and not state.has_gold:
                continue

            next_health = state.health - 1
            pit_cost = 0
            if cell == "P":
                next_health //= 2
                pit_cost = self.config.pit_penalty
            if next_health <= 0:
                continue

            next_has_gold = state.has_gold or next_position in self.gold_positions
            health_loss = state.health - next_health
            transition_cost = health_loss + pit_cost
            successors.append(
                (
                    action,
                    SearchState(next_position, next_health, next_has_gold),
                    transition_cost,
                )
            )
        return successors

    def _heuristic(self, state: SearchState) -> int:
        if state.has_gold:
            return self._manhattan(state.position, self.config.exit_position)
        return min(
            self._manhattan(state.position, gold)
            + self._manhattan(gold, self.config.exit_position)
            for gold in self.gold_positions
        )

    def _inside(self, position: tuple[int, int]) -> bool:
        row, col = position
        return 0 <= row < self.rows and 0 <= col < self.cols

    def _cell_at(self, position: tuple[int, int]) -> str:
        row, col = position
        return self.config.grid[row][col]

    @staticmethod
    def _manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    @staticmethod
    def _reconstruct(
        came_from: dict[SearchState, tuple[SearchState, Action]],
        goal: SearchState,
    ) -> tuple[tuple[Action, ...], tuple[tuple[int, int], ...]]:
        actions: list[Action] = []
        path: list[tuple[int, int]] = [goal.position]
        current = goal
        while current in came_from:
            previous, action = came_from[current]
            actions.append(action)
            path.append(previous.position)
            current = previous
        actions.reverse()
        path.reverse()
        return tuple(actions), tuple(path)
