from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any, Mapping, Protocol


class AgentRunner(Protocol):
    """Minimal contract required by the workflow orchestrator."""

    def run(self, case: Any) -> Any:
        ...


@dataclass(frozen=True, slots=True)
class WorkflowContext:
    """Request-specific dependencies for one governed workflow execution.

    A context owns the agent registry and runtime status used by one case run.
    The mappings are copied and made read-only so another browser session cannot
    replace the registry while a workflow is running.
    """

    agent_registry: Mapping[str, AgentRunner]
    runtime_status: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "agent_registry",
            MappingProxyType(dict(self.agent_registry)),
        )
        object.__setattr__(
            self,
            "runtime_status",
            MappingProxyType(dict(self.runtime_status)),
        )

    def agent(self, agent_id: str) -> AgentRunner:
        """Return one configured agent or fail clearly if routing is invalid."""
        try:
            return self.agent_registry[agent_id]
        except KeyError as exc:
            raise KeyError(
                f"WorkflowContext has no configured agent for routed channel {agent_id!r}."
            ) from exc

    def status_snapshot(self) -> dict[str, Any]:
        """Return a normal dictionary suitable for UI display and serialization."""
        return dict(self.runtime_status)
