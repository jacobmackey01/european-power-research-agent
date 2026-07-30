from __future__ import annotations

from copy import deepcopy
from typing import Any

from power_research_agent.models import (
    CONCLUSIONS,
    ROOT_CAUSES,
    AgentReport,
    EpisodeSpec,
    ToolEvent,
)

ANALYSIS_TOOLS = (
    "inspect_market_context",
    "run_data_quality_checks",
    "run_walk_forward_validation",
    "run_statistical_inference",
    "run_strategy_stress_test",
)
FINAL_TOOL = "submit_research_memo"


def function_tools() -> list[dict[str, Any]]:
    """Return lean, strict Responses API function-tool definitions."""

    return [
        _function_tool(
            "inspect_market_context",
            "Return source, market, unit, time-zone, and split metadata.",
            {},
            [],
        ),
        _function_tool(
            "run_data_quality_checks",
            "Run deterministic timestamp, missingness, unit, and leakage checks.",
            {
                "checks": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Checks relevant to the current hypothesis.",
                }
            },
            ["checks"],
        ),
        _function_tool(
            "run_walk_forward_validation",
            "Return pre-computed chronological fold and holdout results.",
            {
                "strategy": {
                    "type": "string",
                    "description": "The candidate strategy being tested.",
                }
            },
            ["strategy"],
        ),
        _function_tool(
            "run_statistical_inference",
            "Return deterministic uncertainty estimates for a named decision metric.",
            {
                "metric": {
                    "type": "string",
                    "description": "The decision metric whose uncertainty should be checked.",
                }
            },
            ["metric"],
        ),
        _function_tool(
            "run_strategy_stress_test",
            "Return pre-computed results under a named cost or market stress.",
            {
                "scenario": {
                    "type": "string",
                    "description": "The stress family to evaluate.",
                }
            },
            ["scenario"],
        ),
        _function_tool(
            FINAL_TOOL,
            "Submit the terminal evidence-cited memo. Call only after investigation.",
            {
                "conclusion": {
                    "type": "string",
                    "enum": list(CONCLUSIONS),
                    "description": "Decision supported by the observed evidence.",
                },
                "root_cause": {
                    "type": "string",
                    "enum": list(ROOT_CAUSES),
                    "description": "Most defensible explanation supported by the evidence.",
                },
                "evidence_ids": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Exact IDs returned by tools that support the memo.",
                },
                "summary": {
                    "type": "string",
                    "description": "Concise decision and evidence chain; do not invent numbers.",
                },
                "risk_assessment": {
                    "type": "string",
                    "description": "Main uncertainty, failure mode, or implementation safeguard.",
                },
            },
            ["conclusion", "root_cause", "evidence_ids", "summary", "risk_assessment"],
        ),
    ]


def _function_tool(
    name: str,
    description: str,
    properties: dict[str, Any],
    required: list[str],
) -> dict[str, Any]:
    return {
        "type": "function",
        "name": name,
        "description": description,
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        },
    }


class ResearchEnvironment:
    """Deterministic tools and auditable event state for one episode."""

    def __init__(self, episode: EpisodeSpec) -> None:
        self.episode = episode
        self.events: list[ToolEvent] = []
        self.report: AgentReport | None = None
        self.observed_evidence_ids: set[str] = set()
        self.invalid_calls = 0

    def execute(self, tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        step = len(self.events) + 1
        duplicate = tool_name in {
            event.tool_name for event in self.events if event.tool_name in ANALYSIS_TOOLS
        }

        if tool_name in ANALYSIS_TOOLS:
            payload = self.episode.tool_payloads.get(tool_name)
            if payload is None:
                result = {
                    "status": "error",
                    "error": f"No deterministic implementation for {tool_name}.",
                }
                self.invalid_calls += 1
            else:
                result = deepcopy(payload)
                self.observed_evidence_ids.update(_evidence_ids(result))
        elif tool_name == FINAL_TOOL:
            result = self._submit(arguments)
        else:
            result = {"status": "error", "error": f"Unknown tool: {tool_name}"}
            self.invalid_calls += 1

        self.events.append(
            ToolEvent(
                step=step,
                tool_name=tool_name,
                arguments=deepcopy(arguments),
                result=deepcopy(result),
                duplicate=duplicate,
            )
        )
        return result

    def record_invalid_call(
        self,
        tool_name: str,
        raw_arguments: str,
        error: str,
    ) -> dict[str, Any]:
        """Record malformed model output so it remains visible to the evaluator."""

        duplicate = tool_name in {
            event.tool_name for event in self.events if event.tool_name in ANALYSIS_TOOLS
        }
        result = {"status": "error", "error": error}
        self.invalid_calls += 1
        self.events.append(
            ToolEvent(
                step=len(self.events) + 1,
                tool_name=tool_name,
                arguments={"raw_arguments": raw_arguments},
                result=deepcopy(result),
                duplicate=duplicate,
            )
        )
        return result

    def _submit(self, arguments: dict[str, Any]) -> dict[str, Any]:
        required = {
            "conclusion",
            "root_cause",
            "evidence_ids",
            "summary",
            "risk_assessment",
        }
        missing = sorted(required.difference(arguments))
        if missing:
            self.invalid_calls += 1
            return {"status": "error", "error": f"Missing fields: {', '.join(missing)}"}

        conclusion = arguments["conclusion"]
        root_cause = arguments["root_cause"]
        evidence_ids = arguments["evidence_ids"]
        if conclusion not in CONCLUSIONS:
            self.invalid_calls += 1
            return {"status": "error", "error": "Invalid conclusion."}
        if root_cause not in ROOT_CAUSES:
            self.invalid_calls += 1
            return {"status": "error", "error": "Invalid root cause."}
        if not isinstance(evidence_ids, list) or not all(
            isinstance(item, str) for item in evidence_ids
        ):
            self.invalid_calls += 1
            return {"status": "error", "error": "evidence_ids must be a list of strings."}
        if not isinstance(arguments["summary"], str) or not isinstance(
            arguments["risk_assessment"], str
        ):
            self.invalid_calls += 1
            return {"status": "error", "error": "Memo fields must be strings."}

        self.report = AgentReport(
            conclusion=conclusion,
            root_cause=root_cause,
            evidence_ids=list(dict.fromkeys(evidence_ids)),
            summary=arguments["summary"],
            risk_assessment=arguments["risk_assessment"],
        )
        unsupported = sorted(set(self.report.evidence_ids) - self.observed_evidence_ids)
        return {
            "status": "accepted",
            "unsupported_evidence_ids": unsupported,
            "message": "Research memo recorded; the evaluator will score it.",
        }

    def public_history(self, limit: int) -> list[dict[str, Any]]:
        """Return a bounded, model-visible tool record for the stateless condition."""

        analytic_events = [event for event in self.events if event.tool_name in ANALYSIS_TOOLS]
        return [
            {
                "step": event.step,
                "tool": event.tool_name,
                "arguments": deepcopy(event.arguments),
                "observation": deepcopy(event.result),
            }
            for event in analytic_events[-limit:]
        ]

    @property
    def duplicate_call_count(self) -> int:
        return sum(event.duplicate for event in self.events)


def _evidence_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_id" and isinstance(item, str):
                found.add(item)
            elif key == "evidence_ids" and isinstance(item, list):
                found.update(entry for entry in item if isinstance(entry, str))
            else:
                found.update(_evidence_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_evidence_ids(item))
    return found
