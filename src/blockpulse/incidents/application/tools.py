"""Validated read-only tools for evidence-grounded investigations."""

from collections.abc import Callable
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from blockpulse.domain.models import EvidencePackage


class ToolRequest(BaseModel):
    """Untrusted request validated before a tool is invoked."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str = Field(min_length=1, max_length=100)
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    """Structured tool output with the evidence IDs it used."""

    tool_name: str
    data: dict[str, Any]
    evidence_ids: list[str] = Field(default_factory=list)


ToolHandler = Callable[[dict[str, Any]], ToolResult]


class ReadOnlyToolRegistry:
    """Allow-list registry; handlers cannot be registered as write operations."""

    def __init__(self) -> None:
        self._handlers: dict[str, ToolHandler] = {}

    def register(self, name: str, handler: ToolHandler) -> None:
        if not name or name in self._handlers:
            raise ValueError(f"Tool name is invalid or already registered: {name!r}")
        self._handlers[name] = handler

    def execute(self, request: ToolRequest) -> ToolResult:
        handler = self._handlers.get(request.tool_name)
        if handler is None:
            raise ValueError(f"Unknown read-only tool: {request.tool_name}")
        result = handler(request.arguments)
        if result.tool_name != request.tool_name:
            raise ValueError("Tool result name does not match requested tool")
        return result


def package_tool_registry(package: EvidencePackage) -> ReadOnlyToolRegistry:
    """Expose only bounded views over one already-built evidence package."""

    registry = ReadOnlyToolRegistry()

    def summary(arguments: dict[str, Any]) -> ToolResult:
        if arguments:
            raise ValueError("incident.summary accepts no arguments")
        return ToolResult(
            tool_name="incident.summary",
            data={
                "incident_id": package.incident_id,
                "detector": package.detector_name,
                "detector_version": package.detector_version,
                "anomaly_score": package.anomaly_score,
                "quality_warnings": package.quality_warnings,
                "unknowns": package.unknowns,
            },
            evidence_ids=[item.evidence_id for item in package.evidence],
        )

    def evidence(arguments: dict[str, Any]) -> ToolResult:
        evidence_id = arguments.get("evidence_id")
        if not isinstance(evidence_id, str) or not evidence_id:
            raise ValueError("incident.evidence requires a non-empty evidence_id")
        selected = next((item for item in package.evidence if item.evidence_id == evidence_id), None)
        if selected is None:
            raise ValueError("Evidence ID is not present in this package")
        return ToolResult(
            tool_name="incident.evidence",
            data=selected.model_dump(mode="json"),
            evidence_ids=[selected.evidence_id],
        )

    registry.register("incident.summary", summary)
    registry.register("incident.evidence", evidence)
    return registry
