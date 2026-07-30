from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from map_parser import MapConfig


class Action(str, Enum):
    UP = "UP"
    DOWN = "DOWN"
    LEFT = "LEFT"
    RIGHT = "RIGHT"


ACTION_DELTAS = {
    Action.UP: (-1, 0),
    Action.DOWN: (1, 0),
    Action.LEFT: (0, -1),
    Action.RIGHT: (0, 1),
}


@dataclass
class GameState:
    position: tuple[int, int] = (0, 0)
    health: int = 0
    collected_gold: int = 0
    pit_entries: int = 0
    steps: int = 0
    score: int = 0
    success: bool = False
    done: bool = False
    termination_reason: str | None = None
    visited: set[tuple[int, int]] = field(default_factory=set)
    history: list[dict[str, Any]] = field(default_factory=list)


class WumpusEnvironment:
    """Deterministic 8x8 Wumpus World shared by all agents."""

    def __init__(self, config: MapConfig):
        self.config = config
        self.rows = len(config.grid)
        self.cols = len(config.grid[0])
        self.remaining_gold: set[tuple[int, int]] = set()
        self.state = GameState()
        self.reset()

    def reset(self) -> dict[str, Any]:
        self.remaining_gold = {
            (r, c)
            for r, row in enumerate(self.config.grid)
            for c, cell in enumerate(row)
            if cell == "G"
        }
        self.state = GameState(
            position=(0, 0),
            health=self.config.initial_health,
            visited={(0, 0)},
        )
        self.state.score = self._calculate_score()
        return self.observe()

    def _inside(self, position: tuple[int, int]) -> bool:
        row, col = position
        return 0 <= row < self.rows and 0 <= col < self.cols

    def cell_at(self, position: tuple[int, int]) -> str:
        if not self._inside(position):
            raise IndexError(f"Position is outside the grid: {position}")
        row, col = position
        return self.config.grid[row][col]

    def neighbors(self, position: tuple[int, int]) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        row, col = position
        for dr, dc in ACTION_DELTAS.values():
            nxt = (row + dr, col + dc)
            if self._inside(nxt):
                result.append(nxt)
        return result

    def valid_actions(self) -> list[Action]:
        valid: list[Action] = []
        row, col = self.state.position
        for action, (dr, dc) in ACTION_DELTAS.items():
            nxt = (row + dr, col + dc)
            if self._inside(nxt) and self.cell_at(nxt) != "D":
                valid.append(action)
        return valid

    def observe(self) -> dict[str, Any]:
        position = self.state.position
        nearby_cells = [self.cell_at(p) for p in self.neighbors(position)]
        current_cell = self.cell_at(position)
        return {
            "position": position,
            "position_one_based": (position[0] + 1, position[1] + 1),
            "health": self.state.health,
            "breeze": "P" in nearby_cells,
            "stench": "W" in nearby_cells,
            "pit_here": current_cell == "P",
            "gold_here": position in self.remaining_gold,
            "has_gold": self.state.collected_gold > 0,
            "at_exit": position == self.config.exit_position,
            "valid_actions": [action.value for action in self.valid_actions()],
            "visited": set(self.state.visited),
        }

    def _calculate_score(self) -> int:
        return (
            self.state.health
            + self.state.collected_gold * self.config.gold_score
            - self.state.pit_entries * self.config.pit_penalty
        )

    def terminate(self, reason: str) -> None:
        if self.state.done:
            return
        if not reason:
            raise ValueError("Termination reason cannot be empty.")
        self.state.done = True
        self.state.success = False
        self.state.termination_reason = reason
        self.state.score = self._calculate_score()

    def step(
        self, action: Action | str
    ) -> tuple[dict[str, Any], int, bool, dict[str, Any]]:
        if self.state.done:
            raise RuntimeError("Episode is finished. Call reset() before taking another action.")

        try:
            action = Action(action)
        except ValueError as exc:
            raise ValueError(f"Unknown action: {action!r}") from exc

        old_score = self.state.score
        old_position = self.state.position
        dr, dc = ACTION_DELTAS[action]
        candidate = (old_position[0] + dr, old_position[1] + dc)
        blocked = not self._inside(candidate) or (
            self._inside(candidate) and self.cell_at(candidate) == "D"
        )

        # Every attempted move, including blocked moves, costs one health point.
        self.state.health -= 1
        self.state.steps += 1

        if not blocked:
            self.state.position = candidate
            self.state.visited.add(candidate)
            cell = self.cell_at(candidate)

            if cell == "W":
                self.state.health = 0
                self.state.done = True
                self.state.success = False
                self.state.termination_reason = "wumpus"
            elif cell == "P":
                self.state.pit_entries += 1
                self.state.health //= 2

            if candidate in self.remaining_gold and not self.state.done:
                self.remaining_gold.remove(candidate)
                self.state.collected_gold += 1

            if candidate == self.config.exit_position and not self.state.done:
                self.state.done = True
                self.state.success = self.state.collected_gold > 0
                self.state.termination_reason = (
                    "escaped_with_gold"
                    if self.state.success
                    else "escaped_without_gold"
                )

        if self.state.health <= 0 and not self.state.done:
            self.state.health = 0
            self.state.done = True
            self.state.success = False
            self.state.termination_reason = "health_depleted"

        self.state.score = self._calculate_score()
        reward = self.state.score - old_score

        event = {
            "step": self.state.steps,
            "action": action.value,
            "from": old_position,
            "to": self.state.position,
            "blocked": blocked,
            "health": self.state.health,
            "score": self.state.score,
            "done": self.state.done,
            "reason": self.state.termination_reason,
        }
        self.state.history.append(event)

        info = {
            "blocked": blocked,
            "score": self.state.score,
            "success": self.state.success,
            "termination_reason": self.state.termination_reason,
            "pit_entries": self.state.pit_entries,
            "collected_gold": self.state.collected_gold,
            "steps": self.state.steps,
        }
        return self.observe(), reward, self.state.done, info

    def render(self) -> str:
        lines: list[str] = []
        agent = self.state.position
        for row_index, row in enumerate(self.config.grid):
            rendered_row: list[str] = []
            for col_index, cell in enumerate(row):
                position = (row_index, col_index)
                if position == agent:
                    rendered_row.append("A")
                elif position == self.config.exit_position:
                    rendered_row.append("E")
                elif cell == "G" and position not in self.remaining_gold:
                    rendered_row.append("*")
                else:
                    rendered_row.append(cell)
            lines.append(" ".join(rendered_row))
        lines.append(
            f"health={self.state.health} gold={self.state.collected_gold} "
            f"steps={self.state.steps} score={self.state.score}"
        )
        return "\n".join(lines)
