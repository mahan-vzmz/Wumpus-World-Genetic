from __future__ import annotations
import random
from typing import Any
from base_agent import BaseAgent
from environment import Action

class RandomAgent(BaseAgent):
    def __init__(self, seed: int = 42):
        self.seed = seed
        self.random = random.Random(seed)

    def reset(self) -> None:
        self.random = random.Random(self.seed)

    def choose_action(self, observation: dict[str, Any]) -> Action:
        actions = [Action(action) for action in observation["valid_actions"]]
        if not actions:
            raise RuntimeError("No valid action is available.")
        return self.random.choice(actions)
