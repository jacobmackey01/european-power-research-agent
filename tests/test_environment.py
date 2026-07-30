from __future__ import annotations

from power_research_agent.environment import ResearchEnvironment, function_tools
from power_research_agent.episodes import get_episode


def test_prompt_does_not_include_answer_key() -> None:
    episode = get_episode("unit-scale-shift")
    prompt = episode.model_prompt()

    assert episode.correct_conclusion not in prompt
    assert episode.correct_root_cause not in prompt
    assert not set(episode.required_evidence_ids).intersection(prompt.split())


def test_environment_tracks_observed_evidence_and_duplicates() -> None:
    environment = ResearchEnvironment(get_episode("dst-transition-duplicate"))

    first = environment.execute("inspect_market_context", {})
    second = environment.execute("inspect_market_context", {})

    assert first["evidence_id"] == "E-DST-META"
    assert second == first
    assert environment.observed_evidence_ids == {"E-DST-META"}
    assert environment.events[0].duplicate is False
    assert environment.events[1].duplicate is True
    assert environment.duplicate_call_count == 1


def test_strict_tool_schemas_require_all_declared_properties() -> None:
    tools = function_tools()

    for tool in tools:
        assert tool["strict"] is True
        parameters = tool["parameters"]
        assert parameters["additionalProperties"] is False
        assert set(parameters["required"]) == set(parameters["properties"])


def test_submission_records_unsupported_ids_for_evaluator() -> None:
    environment = ResearchEnvironment(get_episode("unit-scale-shift"))
    environment.execute("inspect_market_context", {})
    result = environment.execute(
        "submit_research_memo",
        {
            "conclusion": "repair_required",
            "root_cause": "unit_scale_shift_gw_as_mw",
            "evidence_ids": ["E-UNIT-META", "E-FABRICATED"],
            "summary": "The metadata supports a repair.",
            "risk_assessment": "Confirm the source contract before rescaling.",
        },
    )

    assert result["status"] == "accepted"
    assert result["unsupported_evidence_ids"] == ["E-FABRICATED"]
    assert environment.report is not None


def test_malformed_call_is_preserved_as_an_error_event() -> None:
    environment = ResearchEnvironment(get_episode("unit-scale-shift"))

    result = environment.record_invalid_call(
        "run_data_quality_checks",
        "{not-json",
        "Invalid JSON arguments.",
    )

    assert result["status"] == "error"
    assert environment.invalid_calls == 1
    assert environment.events[0].arguments == {"raw_arguments": "{not-json"}
    assert environment.events[0].result["error"] == "Invalid JSON arguments."
