from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from power_research_agent.environment import FINAL_TOOL, ResearchEnvironment, function_tools
from power_research_agent.models import HarnessMode, RunResult, UsageTotals

SYSTEM_INSTRUCTIONS = """\
You are an evidence-led European power-market research agent.

Choose one tool at a time. Use deterministic tools for every quantitative claim:
do not calculate, interpolate, or invent values yourself. Treat tool observations
as evidence, revise your hypothesis when they conflict, and avoid repeating a
deterministic call. A plausible uplift is not a robust edge unless chronological
validation, uncertainty, and cost stress support it.

Your terminal action must be submit_research_memo. Cite only exact evidence IDs
you actually observed. State uncertainty plainly. Do not answer in free text.
"""


@dataclass(frozen=True)
class HarnessConfig:
    mode: HarnessMode = HarnessMode.RETAINED_REASONING_COMPACTION
    model: str = "gpt-5.6-sol"
    reasoning_effort: str = "max"
    max_steps: int = 8
    max_output_tokens: int = 4096
    compact_threshold: int = 200_000
    stateless_history_window: int = 3
    service_tier: str = "default"

    def __post_init__(self) -> None:
        allowed_efforts = {"none", "low", "medium", "high", "xhigh", "max"}
        if self.reasoning_effort not in allowed_efforts:
            raise ValueError(f"Unsupported reasoning effort: {self.reasoning_effort}")
        if self.max_steps < 1:
            raise ValueError("max_steps must be positive.")
        if self.max_output_tokens < 128:
            raise ValueError("max_output_tokens must be at least 128.")
        if self.compact_threshold < 1_000:
            raise ValueError("compact_threshold must be at least 1,000 tokens.")
        if self.stateless_history_window < 1:
            raise ValueError("stateless_history_window must be positive.")
        if self.service_tier not in {"auto", "default", "flex"}:
            raise ValueError(f"Unsupported service tier: {self.service_tier}")


class ResponsesHarness:
    """Run one deterministic episode through a selected Responses API condition."""

    def __init__(self, config: HarnessConfig, client: Any | None = None) -> None:
        self.config = config
        if client is None:
            from openai import OpenAI

            client = OpenAI()
        self.client = client

    def run(self, environment: ResearchEnvironment) -> RunResult:
        started = time.perf_counter()
        usage = UsageTotals()
        response_ids: list[str] = []
        response_models: list[str] = []
        effective_reasoning_contexts: list[str] = []
        service_tiers: list[str] = []
        errors: list[str] = []
        compaction_events = 0
        previous_response_id: str | None = None
        next_input: str | list[dict[str, Any]] = environment.episode.model_prompt()

        for _ in range(self.config.max_steps):
            request = self._request(
                environment=environment,
                next_input=next_input,
                previous_response_id=previous_response_id,
            )
            try:
                response = self.client.responses.create(**request)
            except Exception as exc:
                errors.append(f"{type(exc).__name__}: {exc}")
                break

            response_id = _field(response, "id")
            if isinstance(response_id, str):
                response_ids.append(response_id)
            response_model = _field(response, "model")
            if isinstance(response_model, str) and response_model not in response_models:
                response_models.append(response_model)
            service_tier = _field(response, "service_tier")
            if isinstance(service_tier, str) and service_tier not in service_tiers:
                service_tiers.append(service_tier)
            reasoning_context = _field(_field(response, "reasoning"), "context")
            if (
                isinstance(reasoning_context, str)
                and reasoning_context not in effective_reasoning_contexts
            ):
                effective_reasoning_contexts.append(reasoning_context)
            compaction_events += _output_item_count(response, "compaction")
            _accumulate_usage(usage, _field(response, "usage"))

            calls = _function_calls(response)
            if not calls:
                output_text = _field(response, "output_text", "")
                detail = f" Free-text output: {output_text}" if output_text else ""
                errors.append(f"Model returned no function call.{detail}")
                break

            call_outputs: list[dict[str, Any]] = []
            for call in calls:
                try:
                    arguments = json.loads(call["arguments"])
                    if not isinstance(arguments, dict):
                        raise TypeError("tool arguments must decode to an object")
                except (json.JSONDecodeError, TypeError) as exc:
                    arguments = {}
                    result = environment.record_invalid_call(
                        call["name"],
                        call["arguments"],
                        f"Invalid JSON arguments: {exc}",
                    )
                else:
                    result = environment.execute(call["name"], arguments)

                call_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": call["call_id"],
                        "output": json.dumps(result, sort_keys=True),
                    }
                )

                if call["name"] == FINAL_TOOL and environment.report is not None:
                    break

            if environment.report is not None:
                break

            if self.config.mode == HarnessMode.STATELESS_TRUNCATED:
                next_input = self._stateless_prompt(environment)
                previous_response_id = None
            else:
                next_input = call_outputs
                previous_response_id = response_id if isinstance(response_id, str) else None
                if previous_response_id is None:
                    errors.append("Response did not contain an ID for continuation.")
                    break
        else:
            errors.append(f"Maximum step budget ({self.config.max_steps}) reached.")

        return RunResult(
            episode_id=environment.episode.episode_id,
            mode=self.config.mode.value,
            model=self.config.model,
            reasoning_effort=self.config.reasoning_effort,
            report=environment.report,
            tool_events=environment.events,
            usage=usage,
            response_ids=response_ids,
            response_models=response_models,
            errors=errors,
            duration_seconds=round(time.perf_counter() - started, 6),
            compact_threshold=(
                self.config.compact_threshold
                if self.config.mode == HarnessMode.RETAINED_REASONING_COMPACTION
                else None
            ),
            compaction_events=compaction_events,
            effective_reasoning_contexts=effective_reasoning_contexts,
            service_tiers=service_tiers,
        )

    def _request(
        self,
        environment: ResearchEnvironment,
        next_input: str | list[dict[str, Any]],
        previous_response_id: str | None,
    ) -> dict[str, Any]:
        retained = self.config.mode != HarnessMode.STATELESS_TRUNCATED
        request: dict[str, Any] = {
            "model": self.config.model,
            "instructions": SYSTEM_INSTRUCTIONS,
            "input": next_input,
            "tools": function_tools(),
            "tool_choice": "required",
            "parallel_tool_calls": False,
            "reasoning": {
                "effort": self.config.reasoning_effort,
                "context": "all_turns" if retained else "current_turn",
            },
            "max_output_tokens": self.config.max_output_tokens,
            "service_tier": self.config.service_tier,
            "store": True,
            "metadata": {
                "project": "european-power-research-agent",
                "episode": environment.episode.episode_id,
                "harness_mode": self.config.mode.value,
            },
        }
        if retained and previous_response_id is not None:
            request["previous_response_id"] = previous_response_id
        if self.config.mode == HarnessMode.RETAINED_REASONING_COMPACTION:
            request["context_management"] = [
                {
                    "type": "compaction",
                    "compact_threshold": self.config.compact_threshold,
                }
            ]
        return request

    def _stateless_prompt(self, environment: ResearchEnvironment) -> str:
        history = environment.public_history(self.config.stateless_history_window)
        return (
            f"{environment.episode.model_prompt()}\n\n"
            "This is a fresh stateless turn. Private reasoning and observations older "
            f"than the last {self.config.stateless_history_window} actions are unavailable.\n"
            "Recent public action record:\n"
            f"{json.dumps(history, indent=2, sort_keys=True)}"
        )


def _function_calls(response: Any) -> list[dict[str, str]]:
    calls: list[dict[str, str]] = []
    for item in _field(response, "output", []) or []:
        if _field(item, "type") != "function_call":
            continue
        name = _field(item, "name")
        arguments = _field(item, "arguments")
        call_id = _field(item, "call_id")
        if all(isinstance(value, str) for value in (name, arguments, call_id)):
            calls.append({"name": name, "arguments": arguments, "call_id": call_id})
    return calls


def _output_item_count(response: Any, item_type: str) -> int:
    return sum(_field(item, "type") == item_type for item in (_field(response, "output", []) or []))


def _accumulate_usage(totals: UsageTotals, usage: Any) -> None:
    if usage is None:
        return
    input_tokens = _as_int(_field(usage, "input_tokens"))
    output_tokens = _as_int(_field(usage, "output_tokens"))
    total_tokens = _as_int(_field(usage, "total_tokens"))
    input_details = _field(usage, "input_tokens_details")
    output_details = _field(usage, "output_tokens_details")

    totals.input_tokens += input_tokens
    totals.output_tokens += output_tokens
    totals.total_tokens += total_tokens or input_tokens + output_tokens
    totals.cached_input_tokens += _as_int(_field(input_details, "cached_tokens"))
    totals.cache_write_tokens += _as_int(_field(input_details, "cache_write_tokens"))
    totals.reasoning_tokens += _as_int(_field(output_details, "reasoning_tokens"))


def _field(value: Any, name: str, default: Any = None) -> Any:
    if value is None:
        return default
    if isinstance(value, dict):
        return value.get(name, default)
    return getattr(value, name, default)


def _as_int(value: Any) -> int:
    return int(value) if isinstance(value, (int, float)) else 0
