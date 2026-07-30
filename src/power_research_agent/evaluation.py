from __future__ import annotations

from statistics import mean
from typing import Any

from power_research_agent.environment import ANALYSIS_TOOLS, ResearchEnvironment
from power_research_agent.models import EpisodeSpec, RunResult, RunScore


def score_run(run: RunResult, episode: EpisodeSpec) -> RunScore:
    """Score a completed run without invoking a model."""

    if run.report is None:
        return RunScore(
            episode_id=episode.episode_id,
            total=0.0,
            components={
                "decision": 0.0,
                "diagnosis": 0.0,
                "required_evidence": 0.0,
                "citation_validity": 0.0,
                "efficiency": 0.0,
            },
            exact_success=False,
            diagnostics={
                "reason": "No research memo submitted.",
                "errors": list(run.errors),
                "tool_calls": len(run.tool_events),
            },
        )

    observed = {
        evidence_id
        for event in run.tool_events
        if event.tool_name in ANALYSIS_TOOLS
        for evidence_id in _evidence_ids(event.result)
    }
    submitted = set(run.report.evidence_ids)
    required = set(episode.required_evidence_ids)
    unsupported = sorted(submitted - observed)
    missing_required = sorted(required - submitted)
    duplicate_calls = sum(event.duplicate for event in run.tool_events)
    invalid_calls = sum(event.result.get("status") == "error" for event in run.tool_events)

    decision = 30.0 if run.report.conclusion == episode.correct_conclusion else 0.0
    diagnosis = 25.0 if run.report.root_cause == episode.correct_root_cause else 0.0
    required_evidence = (
        25.0 * len(required.intersection(submitted)) / len(required) if required else 25.0
    )
    citation_validity = 10.0 if submitted and not unsupported else 0.0
    efficiency = max(0.0, 10.0 - 5.0 * duplicate_calls - 5.0 * invalid_calls)

    components = {
        "decision": decision,
        "diagnosis": diagnosis,
        "required_evidence": round(required_evidence, 3),
        "citation_validity": citation_validity,
        "efficiency": efficiency,
    }
    total = round(sum(components.values()), 3)
    exact_success = (
        decision == 30.0 and diagnosis == 25.0 and not missing_required and not unsupported
    )
    return RunScore(
        episode_id=episode.episode_id,
        total=total,
        components=components,
        exact_success=exact_success,
        diagnostics={
            "missing_required_evidence_ids": missing_required,
            "unsupported_evidence_ids": unsupported,
            "duplicate_calls": duplicate_calls,
            "invalid_calls": invalid_calls,
            "observed_evidence_ids": sorted(observed),
            "submitted_evidence_ids": sorted(submitted),
            "errors": list(run.errors),
        },
    )


def benchmark_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate already-scored records by harness mode."""

    grouped: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        grouped.setdefault(record["run"]["mode"], []).append(record)

    by_mode: dict[str, Any] = {}
    for mode, mode_records in grouped.items():
        scores = [float(record["score"]["total"]) for record in mode_records]
        successes = [bool(record["score"]["exact_success"]) for record in mode_records]
        by_mode[mode] = {
            "runs": len(mode_records),
            "mean_score": round(mean(scores), 3),
            "exact_success_rate": round(sum(successes) / len(successes), 3),
            "input_tokens": sum(record["run"]["usage"]["input_tokens"] for record in mode_records),
            "output_tokens": sum(
                record["run"]["usage"]["output_tokens"] for record in mode_records
            ),
            "reasoning_tokens": sum(
                record["run"]["usage"]["reasoning_tokens"] for record in mode_records
            ),
            "duration_seconds": round(
                sum(record["run"]["duration_seconds"] for record in mode_records), 3
            ),
        }
    return {"runs": len(records), "by_mode": by_mode}


def score_environment(run: RunResult, environment: ResearchEnvironment) -> RunScore:
    """Convenience wrapper for callers that retain the environment."""

    return score_run(run, environment.episode)


def _evidence_ids(value: Any) -> set[str]:
    found: set[str] = set()
    if isinstance(value, dict):
        for key, item in value.items():
            if key == "evidence_id" and isinstance(item, str):
                found.add(item)
            else:
                found.update(_evidence_ids(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_evidence_ids(item))
    return found
