from __future__ import annotations

import hashlib
import itertools
import random
from statistics import mean
from typing import Any

from power_research_agent.environment import ANALYSIS_TOOLS, ResearchEnvironment
from power_research_agent.models import EpisodeSpec, RunResult, RunScore


def score_run(run: RunResult, episode: EpisodeSpec) -> RunScore:
    """Score a completed run without invoking a model."""

    observed = {
        evidence_id
        for event in run.tool_events
        if event.tool_name in ANALYSIS_TOOLS
        for evidence_id in _evidence_ids(event.result)
    }
    duplicate_calls = sum(event.duplicate for event in run.tool_events)
    invalid_calls = sum(event.result.get("status") == "error" for event in run.tool_events)
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
                "duplicate_calls": duplicate_calls,
                "invalid_calls": invalid_calls,
                "observed_evidence_ids": sorted(observed),
            },
        )

    submitted = set(run.report.evidence_ids)
    required = set(episode.required_evidence_ids)
    unsupported = sorted(submitted - observed)
    missing_required = sorted(required - submitted)
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
            "cached_input_tokens": sum(
                record["run"]["usage"].get("cached_input_tokens", 0)
                for record in mode_records
            ),
            "cache_write_tokens": sum(
                record["run"]["usage"].get("cache_write_tokens", 0)
                for record in mode_records
            ),
            "output_tokens": sum(
                record["run"]["usage"]["output_tokens"] for record in mode_records
            ),
            "reasoning_tokens": sum(
                record["run"]["usage"]["reasoning_tokens"] for record in mode_records
            ),
            "duration_seconds": round(
                sum(record["run"]["duration_seconds"] for record in mode_records), 3
            ),
            "compaction_events": sum(
                record["run"].get("compaction_events", 0) for record in mode_records
            ),
            "estimated_cost_usd": round(
                sum(float(record.get("estimated_cost_usd", 0.0)) for record in mode_records),
                6,
            ),
        }
    return {"runs": len(records), "by_mode": by_mode}


def estimate_cost_usd(run: dict[str, Any], pricing: dict[str, float]) -> float:
    """Estimate one run at a recorded per-million-token price snapshot."""

    usage = run["usage"]
    input_tokens = int(usage.get("input_tokens", 0))
    cached_tokens = int(usage.get("cached_input_tokens", 0))
    cache_write_tokens = int(usage.get("cache_write_tokens", 0))
    output_tokens = int(usage.get("output_tokens", 0))
    uncached_tokens = max(0, input_tokens - cached_tokens - cache_write_tokens)
    cost = (
        uncached_tokens * pricing["input_per_million"]
        + cached_tokens * pricing["cached_input_per_million"]
        + cache_write_tokens * pricing.get(
            "cache_write_per_million", pricing["input_per_million"]
        )
        + output_tokens * pricing["output_per_million"]
    ) / 1_000_000
    return round(cost, 8)


def paired_comparisons(
    records: list[dict[str, Any]],
    comparison_specs: list[dict[str, Any]],
    *,
    bootstrap_seed: int,
    bootstrap_iterations: int = 20_000,
) -> dict[str, Any]:
    """Compute episode-clustered paired estimates for preregistered contrasts."""

    if bootstrap_iterations < 1_000:
        raise ValueError("Use at least 1,000 bootstrap iterations.")
    indexed: dict[tuple[str, int, str], dict[str, Any]] = {}
    for record in records:
        episode_id = str(record["run"]["episode_id"])
        repeat_index = int(record.get("repeat_index", 0))
        mode = str(record["run"]["mode"])
        key = (episode_id, repeat_index, mode)
        if key in indexed:
            raise ValueError(f"Duplicate paired record: {key}")
        indexed[key] = record

    results: dict[str, Any] = {}
    for spec in comparison_specs:
        name = str(spec["name"])
        control = str(spec["control"])
        treatment = str(spec["treatment"])
        pairs: list[tuple[dict[str, Any], dict[str, Any]]] = []
        for episode_id, repeat_index, mode in sorted(indexed):
            if mode != control:
                continue
            control_record = indexed[(episode_id, repeat_index, control)]
            treatment_record = indexed.get((episode_id, repeat_index, treatment))
            if treatment_record is not None:
                pairs.append((control_record, treatment_record))

        comparison: dict[str, Any] = {
            "control": control,
            "treatment": treatment,
            "paired_runs": len(pairs),
            "episodes": len({pair[0]["run"]["episode_id"] for pair in pairs}),
        }
        expected_pairs = int(spec.get("expected_pairs", len(pairs)))
        comparison["complete"] = len(pairs) == expected_pairs
        if not pairs:
            comparison["error"] = "No complete pairs are available."
            results[name] = comparison
            continue

        metrics = {
            "score": lambda record: float(record["score"]["total"]),
            "exact_success": lambda record: float(bool(record["score"]["exact_success"])),
            "input_tokens": lambda record: float(record["run"]["usage"]["input_tokens"]),
            "output_tokens": lambda record: float(record["run"]["usage"]["output_tokens"]),
            "reasoning_tokens": lambda record: float(
                record["run"]["usage"]["reasoning_tokens"]
            ),
            "duration_seconds": lambda record: float(record["run"]["duration_seconds"]),
            "estimated_cost_usd": lambda record: float(
                record.get("estimated_cost_usd", 0.0)
            ),
        }
        comparison["metrics"] = {
            metric: _paired_metric(
                pairs,
                getter,
                bootstrap_seed=_derived_seed(bootstrap_seed, name, metric),
                bootstrap_iterations=bootstrap_iterations,
            )
            for metric, getter in metrics.items()
        }
        treatment_runs = [pair[1] for pair in pairs]
        compaction_runs = [
            record
            for record in treatment_runs
            if record["run"]["mode"] == "retained-reasoning-compaction"
        ]
        if compaction_runs:
            activated = sum(
                record["run"].get("compaction_events", 0) > 0
                for record in compaction_runs
            )
            comparison["compaction_activation"] = {
                "runs_with_compaction": activated,
                "runs": len(compaction_runs),
                "rate": round(activated / len(compaction_runs), 6),
                "events": sum(
                    int(record["run"].get("compaction_events", 0))
                    for record in compaction_runs
                ),
            }
        results[name] = comparison
    return results


def _paired_metric(
    pairs: list[tuple[dict[str, Any], dict[str, Any]]],
    getter: Any,
    *,
    bootstrap_seed: int,
    bootstrap_iterations: int,
) -> dict[str, Any]:
    by_episode: dict[str, list[tuple[float, float]]] = {}
    for control_record, treatment_record in pairs:
        episode_id = str(control_record["run"]["episode_id"])
        by_episode.setdefault(episode_id, []).append(
            (getter(control_record), getter(treatment_record))
        )
    clusters = [
        (
            mean(control for control, _ in values),
            mean(treatment for _, treatment in values),
        )
        for _, values in sorted(by_episode.items())
    ]
    control_values = [control for control, _ in clusters]
    treatment_values = [treatment for _, treatment in clusters]
    deltas = [treatment - control for control, treatment in clusters]
    rng = random.Random(bootstrap_seed)
    bootstrapped = [
        mean(rng.choice(deltas) for _ in deltas) for _ in range(bootstrap_iterations)
    ]
    control_mean = mean(control_values)
    treatment_mean = mean(treatment_values)
    delta = mean(deltas)
    ratio = treatment_mean / control_mean if control_mean else None
    return {
        "control_mean": round(control_mean, 6),
        "treatment_mean": round(treatment_mean, 6),
        "delta": round(delta, 6),
        "delta_ci_95": [
            round(_percentile(bootstrapped, 0.025), 6),
            round(_percentile(bootstrapped, 0.975), 6),
        ],
        "treatment_to_control_ratio": round(ratio, 6) if ratio is not None else None,
        "episode_level_better_tied_worse": [
            sum(value > 0 for value in deltas),
            sum(value == 0 for value in deltas),
            sum(value < 0 for value in deltas),
        ],
        "two_sided_sign_flip_p": _sign_flip_p_value(deltas),
    }


def _sign_flip_p_value(deltas: list[float]) -> float:
    nonzero = [value for value in deltas if value != 0]
    if not nonzero:
        return 1.0
    observed = abs(mean(nonzero))
    if len(nonzero) <= 20:
        values = (
            abs(mean(sign * value for sign, value in zip(signs, nonzero, strict=True)))
            for signs in itertools.product((-1, 1), repeat=len(nonzero))
        )
        total = 2 ** len(nonzero)
        extreme = sum(value >= observed - 1e-12 for value in values)
        return round(extreme / total, 6)

    rng = random.Random(_derived_seed(0, "sign-flip", str(len(nonzero))))
    iterations = 100_000
    extreme = 0
    for _ in range(iterations):
        randomized = abs(mean(rng.choice((-1, 1)) * value for value in nonzero))
        extreme += randomized >= observed - 1e-12
    return round((extreme + 1) / (iterations + 1), 6)


def _percentile(values: list[float], probability: float) -> float:
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    weight = position - lower
    return ordered[lower] * (1 - weight) + ordered[upper] * weight


def _derived_seed(seed: int, *parts: str) -> int:
    digest = hashlib.sha256("|".join((str(seed), *parts)).encode()).digest()
    return int.from_bytes(digest[:8], "big")


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
