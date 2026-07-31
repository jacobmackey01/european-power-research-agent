from __future__ import annotations

from power_research_agent.environment import ResearchEnvironment
from power_research_agent.episodes import get_episode
from power_research_agent.evaluation import (
    benchmark_summary,
    estimate_cost_usd,
    paired_comparisons,
    score_run,
)
from power_research_agent.models import RunResult, UsageTotals


def _completed_run(environment: ResearchEnvironment) -> RunResult:
    return RunResult(
        episode_id=environment.episode.episode_id,
        mode="retained-reasoning",
        model="gpt-5.6-sol",
        reasoning_effort="max",
        report=environment.report,
        tool_events=environment.events,
        usage=UsageTotals(input_tokens=100, output_tokens=40, reasoning_tokens=20),
    )


def test_correct_evidence_cited_report_scores_100() -> None:
    episode = get_episode("regime-dependent-signal")
    environment = ResearchEnvironment(episode)
    environment.execute(
        "run_walk_forward_validation",
        {"strategy": "weather-conditioned residual model"},
    )
    environment.execute(
        "run_statistical_inference",
        {"metric": "net value change"},
    )
    environment.execute(
        "run_strategy_stress_test",
        {"scenario": "cost and market regimes"},
    )
    environment.execute(
        "submit_research_memo",
        {
            "conclusion": "no_robust_edge",
            "root_cause": "regime_dependent_signal",
            "evidence_ids": ["E-REGIME-WF", "E-REGIME-INF", "E-REGIME-STRESS"],
            "summary": "The mixed folds, interval crossing zero, and stress losses reject an edge.",
            "risk_assessment": "Do not promote without a new prospective holdout.",
        },
    )

    score = score_run(_completed_run(environment), episode)

    assert score.total == 100.0
    assert score.exact_success is True
    assert score.diagnostics["unsupported_evidence_ids"] == []


def test_fabricated_citation_loses_validity_points() -> None:
    episode = get_episode("dst-transition-duplicate")
    environment = ResearchEnvironment(episode)
    environment.execute("inspect_market_context", {})
    environment.execute(
        "submit_research_memo",
        {
            "conclusion": "repair_required",
            "root_cause": "dst_duplicate_local_hour",
            "evidence_ids": ["E-DST-META", "E-MADE-UP"],
            "summary": "The local timestamp needs repair.",
            "risk_assessment": "Normalize to UTC.",
        },
    )

    score = score_run(_completed_run(environment), episode)

    assert score.total == 77.5
    assert score.exact_success is False
    assert score.diagnostics["unsupported_evidence_ids"] == ["E-MADE-UP"]
    assert score.diagnostics["missing_required_evidence_ids"] == ["E-DST-QUALITY"]


def test_missing_report_scores_zero() -> None:
    episode = get_episode("dst-transition-duplicate")
    run = RunResult(
        episode_id=episode.episode_id,
        mode="stateless-truncated",
        model="gpt-5.6-sol",
        reasoning_effort="max",
        report=None,
        tool_events=[],
        usage=UsageTotals(),
        errors=["Maximum step budget reached."],
    )

    score = score_run(run, episode)

    assert score.total == 0.0
    assert score.exact_success is False


def test_benchmark_summary_groups_conditions() -> None:
    records = [
        {
            "run": {
                "mode": "retained-reasoning",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 20,
                    "reasoning_tokens": 10,
                },
                "duration_seconds": 1.5,
            },
            "score": {"total": 100.0, "exact_success": True},
        },
        {
            "run": {
                "mode": "retained-reasoning",
                "usage": {
                    "input_tokens": 120,
                    "output_tokens": 30,
                    "reasoning_tokens": 15,
                },
                "duration_seconds": 2.0,
            },
            "score": {"total": 50.0, "exact_success": False},
        },
    ]

    summary = benchmark_summary(records)

    assert summary["runs"] == 2
    assert summary["by_mode"]["retained-reasoning"]["mean_score"] == 75.0
    assert summary["by_mode"]["retained-reasoning"]["exact_success_rate"] == 0.5
    assert summary["by_mode"]["retained-reasoning"]["input_tokens"] == 220


def test_cost_estimate_separates_cached_and_cache_write_tokens() -> None:
    run = {
        "usage": {
            "input_tokens": 1_000,
            "cached_input_tokens": 200,
            "cache_write_tokens": 100,
            "output_tokens": 300,
        }
    }
    pricing = {
        "input_per_million": 5.0,
        "cached_input_per_million": 0.5,
        "cache_write_per_million": 6.25,
        "output_per_million": 30.0,
    }

    assert estimate_cost_usd(run, pricing) == 0.013225


def test_paired_comparison_clusters_repeats_by_episode() -> None:
    records = []
    for episode_id, control_score, treatment_score in (
        ("episode-a", 40.0, 90.0),
        ("episode-b", 60.0, 100.0),
    ):
        for repeat_index in (1, 2):
            for mode, score in (
                ("stateless-truncated", control_score),
                ("retained-reasoning", treatment_score),
            ):
                records.append(
                    {
                        "repeat_index": repeat_index,
                        "run": {
                            "episode_id": episode_id,
                            "mode": mode,
                            "usage": {
                                "input_tokens": 100,
                                "output_tokens": 20,
                                "reasoning_tokens": 10,
                            },
                            "duration_seconds": 1.0,
                        },
                        "score": {"total": score, "exact_success": score == 100.0},
                        "estimated_cost_usd": 0.01,
                    }
                )

    result = paired_comparisons(
        records,
        [
            {
                "name": "retention",
                "control": "stateless-truncated",
                "treatment": "retained-reasoning",
                "expected_pairs": 4,
            }
        ],
        bootstrap_seed=7,
        bootstrap_iterations=1_000,
    )["retention"]

    assert result["complete"] is True
    assert result["paired_runs"] == 4
    assert result["episodes"] == 2
    assert result["metrics"]["score"]["delta"] == 45.0
