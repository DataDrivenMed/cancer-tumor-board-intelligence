from __future__ import annotations

from abc import ABC, abstractmethod
from schemas.agent import AgentOutput
from schemas.case import CancerTumorBoardCase


class BaseAgent(ABC):
    agent_id: str = "base"

    @abstractmethod
    def run(self, case: CancerTumorBoardCase) -> AgentOutput:
        raise NotImplementedError
