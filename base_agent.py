from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from environment import Action


class BaseAgent(ABC):
    @abstractmethod
    def reset(self) -> None:
        """Reset agent memory before a new episode."""

    @abstractmethod
    def choose_action(self, observation: dict[str, Any]) -> Action:
        raise NotImplementedError
