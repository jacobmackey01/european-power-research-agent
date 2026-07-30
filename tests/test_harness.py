from __future__ import annotations

from conftest import FakeClient, function_call_response

from power_research_agent.environment import ResearchEnvironment
from power_research_agent.episodes import get_episode
from power_research_agent.harness import HarnessConfig, ResponsesHarness
from power_research_agent.models import HarnessMode


def _scripted_unit_scale_run() -> list:
    return [
        function_call_response("resp-1", "inspect_market_context", {}),
        function_call_response(
            "resp-2",
            "run_data_quality_checks",
            {"checks": ["units", "change points", "adjacent feeds"]},
        ),
        function_call_response(
            "resp-3",
            "submit_research_memo",
            {
                "conclusion": "repair_required",
                "root_cause": "unit_scale_shift_gw_as_mw",
                "evidence_ids": ["E-UNIT-META", "E-UNIT-QUALITY"],
                "summary": "A 1,000-fold scale break is a unit defect, not market behaviour.",
                "risk_assessment": "Confirm the vendor contract before repairing history.",
            },
        ),
    ]


def test_retained_reasoning_continues_with_previous_response_id() -> None:
    client = FakeClient(_scripted_unit_scale_run())
    environment = ResearchEnvironment(get_episode("unit-scale-shift"))
    config = HarnessConfig(
        mode=HarnessMode.RETAINED_REASONING,
        reasoning_effort="high",
    )

    run = ResponsesHarness(config, client=client).run(environment)
    requests = client.responses.requests

    assert run.report is not None
    assert run.errors == []
    assert "previous_response_id" not in requests[0]
    assert requests[1]["previous_response_id"] == "resp-1"
    assert requests[2]["previous_response_id"] == "resp-2"
    assert all(request["reasoning"]["context"] == "all_turns" for request in requests)
    assert all("context_management" not in request for request in requests)
    assert requests[1]["input"][0]["type"] == "function_call_output"
    assert run.usage.input_tokens == 30
    assert run.usage.output_tokens == 15
    assert run.usage.reasoning_tokens == 9


def test_compaction_condition_adds_context_management() -> None:
    client = FakeClient(_scripted_unit_scale_run())
    environment = ResearchEnvironment(get_episode("unit-scale-shift"))
    config = HarnessConfig(
        mode=HarnessMode.RETAINED_REASONING_COMPACTION,
        compact_threshold=175_000,
    )

    run = ResponsesHarness(config, client=client).run(environment)

    assert run.report is not None
    assert run.compact_threshold == 175_000
    for request in client.responses.requests:
        assert request["context_management"] == [
            {"type": "compaction", "compact_threshold": 175_000}
        ]


def test_stateless_condition_never_uses_native_continuation() -> None:
    client = FakeClient(_scripted_unit_scale_run())
    environment = ResearchEnvironment(get_episode("unit-scale-shift"))
    config = HarnessConfig(
        mode=HarnessMode.STATELESS_TRUNCATED,
        stateless_history_window=1,
    )

    run = ResponsesHarness(config, client=client).run(environment)
    requests = client.responses.requests

    assert run.report is not None
    assert all("previous_response_id" not in request for request in requests)
    assert all("context_management" not in request for request in requests)
    assert all(request["reasoning"]["context"] == "current_turn" for request in requests)
    assert "E-UNIT-META" in requests[1]["input"]
    assert "E-UNIT-META" not in requests[2]["input"]
    assert "E-UNIT-QUALITY" in requests[2]["input"]
