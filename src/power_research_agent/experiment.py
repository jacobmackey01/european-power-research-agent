from __future__ import annotations

import hashlib
import json
import random
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from power_research_agent.benchmark import SealedSuite, load_sealed_suite, sha256_file
from power_research_agent.environment import ResearchEnvironment
from power_research_agent.evaluation import (
    benchmark_summary,
    estimate_cost_usd,
    paired_comparisons,
    score_run,
)
from power_research_agent.harness import HarnessConfig, ResponsesHarness
from power_research_agent.models import HarnessMode


@dataclass(frozen=True)
class ExperimentJob:
    job_id: str
    episode_id: str
    repeat_index: int
    mode: HarnessMode
    execution_order: int


def run_preregistered_experiment(
    *,
    preregistration_path: Path,
    episodes_path: Path,
    answers_path: Path,
    output_path: Path,
    resume: bool,
    client: Any | None = None,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Execute, checkpoint, and analyze a hash-locked paid experiment."""

    progress = progress or (lambda _: None)
    manifest = _load_object(preregistration_path)
    manifest_hash = sha256_file(preregistration_path)
    suite = load_sealed_suite(
        episodes_path,
        answers_path,
        preregistration_path=preregistration_path,
    )
    jobs = build_jobs(manifest, suite, manifest_hash)
    pricing = _pricing(manifest)

    payload = _initial_payload(manifest, manifest_hash, suite, jobs)
    if output_path.exists():
        if not resume:
            raise FileExistsError(
                f"{output_path} already exists. Pass --resume to continue the same matrix."
            )
        payload = _load_object(output_path)
        if payload.get("preregistration_sha256") != manifest_hash:
            raise ValueError("Existing output belongs to a different preregistration.")
    completed_ids = {str(record["job_id"]) for record in payload.get("records", [])}

    if client is None:
        from openai import OpenAI

        client = OpenAI()

    episode_by_id = {episode.episode_id: episode for episode in suite.episodes}
    fatal_error: str | None = None
    budget_stopped = False
    for job in jobs:
        if job.job_id in completed_ids:
            continue
        if _budget_guard_reached(payload, manifest):
            payload["status"] = "interrupted"
            payload["interruption_reason"] = (
                "The preregistered client-side estimated-cost guard stopped before "
                "the next paid run. The incomplete matrix cannot support a claim."
            )
            payload["updated_utc"] = _utc_now()
            _atomic_write_json(output_path, payload)
            budget_stopped = True
            break
        progress(
            f"[{job.execution_order}/{len(jobs)}] {job.episode_id} | "
            f"repeat {job.repeat_index} | {job.mode.value}"
        )
        episode = episode_by_id[job.episode_id]
        environment = ResearchEnvironment(episode)
        config = _harness_config(manifest, job.mode)
        run = ResponsesHarness(config, client=client).run(environment)
        score = score_run(run, episode)
        run_dict = run.to_dict()
        record = {
            "job_id": job.job_id,
            "execution_order": job.execution_order,
            "repeat_index": job.repeat_index,
            "run": run_dict,
            "score": score.to_dict(),
            "estimated_cost_usd": estimate_cost_usd(run_dict, pricing),
        }
        payload["records"].append(record)
        completed_ids.add(job.job_id)
        payload["completed_runs"] = len(payload["records"])
        payload["status"] = "running"
        payload["updated_utc"] = _utc_now()
        _refresh_analysis(payload, manifest)
        _atomic_write_json(output_path, payload)

        fatal_error = _fatal_api_error(run.errors)
        if fatal_error:
            payload["status"] = "interrupted"
            payload["interruption_reason"] = fatal_error
            _atomic_write_json(output_path, payload)
            break

    if fatal_error is None and not budget_stopped and len(payload["records"]) == len(jobs):
        payload["status"] = "complete"
        payload["completed_utc"] = _utc_now()
        payload.pop("interruption_reason", None)
        _refresh_analysis(payload, manifest)
        _atomic_write_json(output_path, payload)
    return payload


def build_jobs(
    manifest: dict[str, Any], suite: SealedSuite, manifest_hash: str
) -> list[ExperimentJob]:
    matrix = _object(manifest.get("run_matrix"), "run_matrix")
    repetitions = _positive_int(matrix.get("repetitions"), "repetitions")
    seed = _integer(matrix.get("randomization_seed"), "randomization_seed")
    raw_modes = matrix.get("modes")
    if not isinstance(raw_modes, list) or not raw_modes:
        raise ValueError("run_matrix.modes must be a non-empty list.")
    modes = [HarnessMode(str(mode)) for mode in raw_modes]
    if len(modes) != len(set(modes)):
        raise ValueError("run_matrix.modes contains duplicates.")

    raw_jobs = [
        (episode.episode_id, repeat_index, mode)
        for episode in sorted(suite.episodes, key=lambda item: item.episode_id)
        for repeat_index in range(1, repetitions + 1)
        for mode in modes
    ]
    random.Random(seed).shuffle(raw_jobs)
    return [
        ExperimentJob(
            job_id=_job_id(manifest_hash, episode_id, repeat_index, mode.value),
            episode_id=episode_id,
            repeat_index=repeat_index,
            mode=mode,
            execution_order=index,
        )
        for index, (episode_id, repeat_index, mode) in enumerate(raw_jobs, start=1)
    ]


def assess_claims(comparisons: dict[str, Any], claim_rules: list[dict[str, Any]]) -> dict[str, Any]:
    """Apply preregistered superiority/non-inferiority rules mechanically."""

    assessed: dict[str, Any] = {}
    for rule in claim_rules:
        name = str(rule["name"])
        comparison = comparisons.get(str(rule["comparison"]))
        metric_name = str(rule["metric"])
        if not comparison or not comparison.get("complete"):
            assessed[name] = {"status": "not_testable", "reason": "Incomplete paired matrix."}
            continue
        if bool(rule.get("requires_compaction")):
            activation = comparison.get("compaction_activation", {})
            minimum = float(rule.get("minimum_compaction_activation_rate", 1.0))
            if float(activation.get("rate", 0.0)) < minimum:
                assessed[name] = {
                    "status": "not_testable",
                    "reason": "Compaction did not activate often enough for this claim.",
                }
                continue

        metric = comparison["metrics"][metric_name]
        lower, upper = metric["delta_ci_95"]
        kind = str(rule["kind"])
        margin = float(rule.get("margin", 0.0))
        alpha = float(rule.get("alpha", 0.05))
        if kind == "superiority":
            supported = lower > margin and metric["two_sided_sign_flip_p"] <= alpha
            rationale = f"95% CI lower bound > {margin} and sign-flip p <= {alpha}."
        elif kind == "noninferiority":
            supported = lower > -margin
            rationale = f"95% CI lower bound > {-margin}."
        elif kind == "reduction":
            supported = upper < -margin
            rationale = f"95% CI upper bound < {-margin}."
        else:
            raise ValueError(f"Unsupported claim-rule kind: {kind}")
        assessed[name] = {
            "status": "supported" if supported else "not_supported",
            "kind": kind,
            "metric": metric_name,
            "observed_delta": metric["delta"],
            "delta_ci_95": metric["delta_ci_95"],
            "rule": rationale,
        }
    return assessed


def _initial_payload(
    manifest: dict[str, Any],
    manifest_hash: str,
    suite: SealedSuite,
    jobs: list[ExperimentJob],
) -> dict[str, Any]:
    return {
        "experiment_id": manifest["experiment_id"],
        "preregistration_sha256": manifest_hash,
        "suite_id": suite.suite_id,
        "episodes_sha256": suite.episodes_sha256,
        "answers_sha256": suite.answers_sha256,
        "status": "not_started",
        "started_utc": _utc_now(),
        "updated_utc": _utc_now(),
        "planned_runs": len(jobs),
        "completed_runs": 0,
        "run_matrix": manifest["run_matrix"],
        "pricing": manifest["pricing"],
        "budget": manifest.get("budget", {}),
        "records": [],
        "summary": {"runs": 0, "by_mode": {}},
        "comparisons": {},
        "claim_assessment": {},
    }


def _refresh_analysis(payload: dict[str, Any], manifest: dict[str, Any]) -> None:
    records = payload["records"]
    payload["summary"] = benchmark_summary(records) if records else {"runs": 0, "by_mode": {}}
    specs = _object_list(manifest.get("comparisons"), "comparisons")
    repetitions = int(manifest["run_matrix"]["repetitions"])
    episode_count = int(manifest["artifacts"]["episode_count"])
    normalized_specs = [{**spec, "expected_pairs": episode_count * repetitions} for spec in specs]
    payload["comparisons"] = paired_comparisons(
        records,
        normalized_specs,
        bootstrap_seed=int(manifest["analysis"]["bootstrap_seed"]),
        bootstrap_iterations=int(manifest["analysis"]["bootstrap_iterations"]),
    )
    payload["claim_assessment"] = assess_claims(
        payload["comparisons"],
        _object_list(manifest.get("claim_rules"), "claim_rules"),
    )


def _harness_config(manifest: dict[str, Any], mode: HarnessMode) -> HarnessConfig:
    matrix = manifest["run_matrix"]
    return HarnessConfig(
        mode=mode,
        model=str(matrix["model"]),
        reasoning_effort=str(matrix["reasoning_effort"]),
        max_steps=int(matrix["max_steps"]),
        max_output_tokens=int(matrix["max_output_tokens"]),
        compact_threshold=int(matrix["compact_threshold"]),
        stateless_history_window=int(matrix["stateless_history_window"]),
        service_tier=str(matrix["service_tier"]),
    )


def _pricing(manifest: dict[str, Any]) -> dict[str, float]:
    pricing = _object(manifest.get("pricing"), "pricing")
    return {
        "input_per_million": float(pricing["input_per_million"]),
        "cached_input_per_million": float(pricing["cached_input_per_million"]),
        "cache_write_per_million": float(pricing["cache_write_per_million"]),
        "output_per_million": float(pricing["output_per_million"]),
    }


def _fatal_api_error(errors: list[str]) -> str | None:
    fatal_names = (
        "AuthenticationError",
        "PermissionDeniedError",
        "BadRequestError",
        "NotFoundError",
        "RateLimitError",
    )
    return next((error for error in errors if error.startswith(fatal_names)), None)


def _budget_guard_reached(payload: dict[str, Any], manifest: dict[str, Any]) -> bool:
    budget = manifest.get("budget")
    if not isinstance(budget, dict):
        return False
    maximum = float(budget["max_estimated_cost_usd"])
    next_run_reserve = float(budget["next_run_reserve_usd"])
    spent = sum(float(record.get("estimated_cost_usd", 0.0)) for record in payload["records"])
    return spent + next_run_reserve > maximum


def _job_id(manifest_hash: str, episode_id: str, repeat_index: int, mode: str) -> str:
    value = f"{manifest_hash}|{episode_id}|{repeat_index}|{mode}".encode()
    return hashlib.sha256(value).hexdigest()[:20]


def _load_object(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    return _object(value, str(path))


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object.")
    return value


def _object_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise ValueError(f"{label} must be a list of objects.")
    return value


def _positive_int(value: Any, label: str) -> int:
    result = _integer(value, label)
    if result < 1:
        raise ValueError(f"{label} must be positive.")
    return result


def _integer(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"{label} must be an integer.")
    return value


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    temporary.replace(path)


def _utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")
