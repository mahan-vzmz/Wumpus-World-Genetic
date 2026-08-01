from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

from wumpus_world.environment import ACTION_DELTAS, Action

Position = tuple[int, int]


@dataclass(frozen=True)
class PerceptRecord:
    breeze: bool
    stench: bool
    pit_here: bool


@dataclass
class KnowledgeBase:
    rows: int
    cols: int
    visited: set[Position] = field(default_factory=set)
    safe: set[Position] = field(default_factory=set)
    walls: set[Position] = field(default_factory=set)
    no_pit: set[Position] = field(default_factory=set)
    no_wumpus: set[Position] = field(default_factory=set)
    possible_pits: set[Position] = field(default_factory=set)
    possible_wumpus: set[Position] = field(default_factory=set)
    definite_pits: set[Position] = field(default_factory=set)
    definite_wumpus: set[Position] = field(default_factory=set)
    percepts: dict[Position, PerceptRecord] = field(default_factory=dict)
    pit_clauses: dict[Position, set[Position]] = field(default_factory=dict)
    wumpus_clauses: dict[Position, set[Position]] = field(default_factory=dict)
    evidence_pit: dict[Position, int] = field(default_factory=dict)
    evidence_wumpus: dict[Position, int] = field(default_factory=dict)
    last_inferences: list[str] = field(default_factory=list)

    def inside(self, position: Position) -> bool:
        row, col = position
        return 0 <= row < self.rows and 0 <= col < self.cols

    def neighbors(self, position: Position) -> list[Position]:
        row, col = position
        result: list[Position] = []
        for dr, dc in ACTION_DELTAS.values():
            nxt = (row + dr, col + dc)
            if self.inside(nxt):
                result.append(nxt)
        return result

    def observe(
        self,
        *,
        position: Position,
        breeze: bool,
        stench: bool,
        pit_here: bool,
        valid_actions: Iterable[str],
    ) -> list[str]:
        self.last_inferences = []
        valid = {Action(action) for action in valid_actions}
        self.visited.add(position)
        self.no_wumpus.add(position)
        if pit_here:
            self.definite_pits.add(position)
            self.safe.discard(position)
            self.last_inferences.append(f"{self._fmt(position)} is a confirmed pit because the agent entered it.")
        else:
            self.no_pit.add(position)
            self.safe.add(position)
        self.percepts[position] = PerceptRecord(
            breeze=breeze,
            stench=stench,
            pit_here=pit_here,
        )

        row, col = position
        traversable_neighbors: set[Position] = set()
        for action, (dr, dc) in ACTION_DELTAS.items():
            nxt = (row + dr, col + dc)
            if not self.inside(nxt):
                continue
            if action in valid:
                traversable_neighbors.add(nxt)
            else:
                self.walls.add(nxt)
                self.last_inferences.append(f"{self._fmt(nxt)} is a wall because movement is blocked.")

        if breeze:
            self.pit_clauses[position] = set(traversable_neighbors)
            self.last_inferences.append("Breeze detected: at least one traversable neighbor may contain a pit.")
        else:
            self.pit_clauses.pop(position, None)
            newly_safe_from_pit = traversable_neighbors - self.no_pit
            self.no_pit.update(traversable_neighbors)
            if newly_safe_from_pit:
                self.last_inferences.append(
                    "No breeze: "
                    + ", ".join(self._fmt(p) for p in sorted(newly_safe_from_pit))
                    + " cannot contain a pit."
                )

        if stench:
            self.wumpus_clauses[position] = set(traversable_neighbors)
            self.last_inferences.append("Stench detected: at least one traversable neighbor may contain a Wumpus.")
        else:
            self.wumpus_clauses.pop(position, None)
            newly_safe_from_wumpus = traversable_neighbors - self.no_wumpus
            self.no_wumpus.update(traversable_neighbors)
            if newly_safe_from_wumpus:
                self.last_inferences.append(
                    "No stench: "
                    + ", ".join(self._fmt(p) for p in sorted(newly_safe_from_wumpus))
                    + " cannot contain a Wumpus."
                )

        self._recompute()
        return list(self.last_inferences)

    def _recompute(self) -> None:
        confirmed_pits = set(self.definite_pits)
        confirmed_wumpus = set(self.definite_wumpus)
        self.evidence_pit = {}
        self.evidence_wumpus = {}
        self.possible_pits = set()
        self.possible_wumpus = set()
        self.definite_pits = confirmed_pits
        self.definite_wumpus = confirmed_wumpus

        for origin, original_clause in self.pit_clauses.items():
            candidates = {p for p in original_clause if p not in self.no_pit and p not in self.walls}
            for candidate in candidates:
                self.evidence_pit[candidate] = self.evidence_pit.get(candidate, 0) + 1
            self.possible_pits.update(candidates)
            if len(candidates) == 1:
                only = next(iter(candidates))
                self.definite_pits.add(only)
                self.last_inferences.append(
                    f"{self._fmt(only)} is a definite pit; it is the only candidate "
                    f"for the breeze at {self._fmt(origin)}."
                )

        for origin, original_clause in self.wumpus_clauses.items():
            candidates = {p for p in original_clause if p not in self.no_wumpus and p not in self.walls}
            for candidate in candidates:
                self.evidence_wumpus[candidate] = self.evidence_wumpus.get(candidate, 0) + 1
            self.possible_wumpus.update(candidates)
            if len(candidates) == 1:
                only = next(iter(candidates))
                self.definite_wumpus.add(only)
                self.last_inferences.append(
                    f"{self._fmt(only)} is a definite Wumpus; it is the only candidate "
                    f"for the stench at {self._fmt(origin)}."
                )

        inferred_safe = self.no_pit & self.no_wumpus
        inferred_safe -= self.walls
        inferred_safe -= self.definite_pits
        inferred_safe -= self.definite_wumpus
        newly_safe = inferred_safe - self.safe
        self.safe.update(inferred_safe)
        self.safe -= self.definite_pits | self.definite_wumpus | self.walls
        if newly_safe:
            self.last_inferences.append(
                "Safe cells inferred: " + ", ".join(self._fmt(p) for p in sorted(newly_safe)) + "."
            )

    def risk(self, position: Position) -> float:
        if position in self.walls or position in self.definite_wumpus:
            return float("inf")
        if position in self.safe:
            return 0.0
        risk = 1.0
        risk += 5.0 * self.evidence_wumpus.get(position, 0)
        risk += 1.5 * self.evidence_pit.get(position, 0)
        if position in self.definite_pits:
            risk += 10.0
        if position in self.visited:
            risk -= 0.25
        return risk

    def status(self, position: Position) -> str:
        if position in self.walls:
            return "WALL"
        if position in self.definite_wumpus:
            return "DEFINITE_WUMPUS"
        if position in self.definite_pits:
            return "DEFINITE_PIT"
        if position in self.safe and position in self.visited:
            return "VISITED_SAFE"
        if position in self.safe:
            return "SAFE"
        if position in self.possible_wumpus and position in self.possible_pits:
            return "POSSIBLE_WUMPUS_OR_PIT"
        if position in self.possible_wumpus:
            return "POSSIBLE_WUMPUS"
        if position in self.possible_pits:
            return "POSSIBLE_PIT"
        return "UNKNOWN"

    def snapshot(self) -> dict[str, list[Position]]:
        return {
            "visited": sorted(self.visited),
            "safe": sorted(self.safe),
            "possible_pits": sorted(self.possible_pits),
            "definite_pits": sorted(self.definite_pits),
            "possible_wumpus": sorted(self.possible_wumpus),
            "definite_wumpus": sorted(self.definite_wumpus),
            "walls": sorted(self.walls),
        }

    @staticmethod
    def _fmt(position: Position) -> str:
        return f"({position[0] + 1},{position[1] + 1})"
