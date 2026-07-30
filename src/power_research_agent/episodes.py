from __future__ import annotations

from copy import deepcopy

from power_research_agent.models import EpisodeSpec

_EPISODES: dict[str, EpisodeSpec] = {
    "dst-transition-duplicate": EpisodeSpec(
        episode_id="dst-transition-duplicate",
        title="Duplicated local hour at the autumn clock change",
        question=(
            "Can this hourly DE-LU price panel be used unchanged for a daily-shape "
            "backtest? If not, identify the most defensible root cause."
        ),
        briefing=(
            "A vendor extract covers 24-26 October 2026. The downstream code groups "
            "observations by naive local timestamp before constructing daily features."
        ),
        correct_conclusion="repair_required",
        correct_root_cause="dst_duplicate_local_hour",
        required_evidence_ids=("E-DST-META", "E-DST-QUALITY"),
        required_tools=("inspect_market_context", "run_data_quality_checks"),
        tool_payloads={
            "inspect_market_context": {
                "status": "ok",
                "evidence_id": "E-DST-META",
                "market": "DE-LU day-ahead",
                "source_timezone": "Europe/Berlin",
                "timestamp_representation": "naive local time",
                "window": "2026-10-24 through 2026-10-26",
                "row_count": 73,
                "downstream_grouping": "calendar date plus local hour",
                "interpretation": (
                    "The window includes the European autumn daylight-saving transition."
                ),
            },
            "run_data_quality_checks": {
                "status": "failed",
                "evidence_id": "E-DST-QUALITY",
                "duplicate_naive_local_timestamps": 1,
                "duplicate_value": "2026-10-25 02:00",
                "source_records_for_duplicate": [
                    {"utc_offset": "+02:00", "price_eur_mwh": 71.4},
                    {"utc_offset": "+01:00", "price_eur_mwh": 68.9},
                ],
                "missing_utc_hours": 0,
                "non_numeric_prices": 0,
                "unit_check": "pass",
                "deterministic_verdict": (
                    "Naive local timestamps are not a unique hourly key. Preserve the "
                    "offset or normalize to UTC before daily feature construction."
                ),
            },
            "run_walk_forward_validation": {
                "status": "not_applicable",
                "evidence_id": "E-DST-WF-NA",
                "reason": "The input key fails quality checks before model validation.",
            },
            "run_statistical_inference": {
                "status": "not_applicable",
                "evidence_id": "E-DST-INF-NA",
                "reason": "Inference is not meaningful until timestamp integrity is repaired.",
            },
            "run_strategy_stress_test": {
                "status": "not_applicable",
                "evidence_id": "E-DST-STRESS-NA",
                "reason": "A strategy test would propagate the duplicated-hour defect.",
            },
        },
    ),
    "unit-scale-shift": EpisodeSpec(
        episode_id="unit-scale-shift",
        title="Silent GW values in an MW-labelled feed",
        question=(
            "A wind-generation feature collapses midway through the sample. Is this "
            "credible market behaviour, or does the dataset require repair?"
        ),
        briefing=(
            "The series is labelled MW throughout. No generation outage is present in "
            "the operator event log, and two adjacent vendor feeds remain continuous."
        ),
        correct_conclusion="repair_required",
        correct_root_cause="unit_scale_shift_gw_as_mw",
        required_evidence_ids=("E-UNIT-META", "E-UNIT-QUALITY"),
        required_tools=("inspect_market_context", "run_data_quality_checks"),
        tool_payloads={
            "inspect_market_context": {
                "status": "ok",
                "evidence_id": "E-UNIT-META",
                "market": "German wind generation",
                "field": "wind_generation_mw",
                "declared_unit": "MW",
                "change_timestamp_utc": "2026-02-01T00:00:00Z",
                "operator_event_log": "no fleet-scale outage",
                "adjacent_source_status": "continuous",
            },
            "run_data_quality_checks": {
                "status": "failed",
                "evidence_id": "E-UNIT-QUALITY",
                "median_7d_before": 34820.0,
                "median_7d_after": 35.1,
                "after_to_before_ratio": 0.001008,
                "correlation_with_adjacent_feed_before": 0.97,
                "correlation_after_rescaling_by_1000": 0.96,
                "label_changed": False,
                "deterministic_verdict": (
                    "Post-change values are in GW while the field remains labelled MW. "
                    "Multiply the affected segment by 1,000 after source confirmation."
                ),
            },
            "run_walk_forward_validation": {
                "status": "blocked",
                "evidence_id": "E-UNIT-WF-BLOCKED",
                "reason": "Validation is blocked by a confirmed unit discontinuity.",
            },
            "run_statistical_inference": {
                "status": "not_applicable",
                "evidence_id": "E-UNIT-INF-NA",
                "reason": "The discontinuity is a measurement-unit defect, not a signal.",
            },
            "run_strategy_stress_test": {
                "status": "not_applicable",
                "evidence_id": "E-UNIT-STRESS-NA",
                "reason": "Strategy stress testing must follow repair and revalidation.",
            },
        },
    ),
    "regime-dependent-signal": EpisodeSpec(
        episode_id="regime-dependent-signal",
        title="A forecasting uplift that does not establish a robust edge",
        question=(
            "Does the residual wind-forecast strategy support a production trading "
            "recommendation after temporal validation, statistical inference, and costs?"
        ),
        briefing=(
            "A candidate model adds weather-driven residual features to a persistence "
            "baseline. The claim must survive chronological folds and plausible costs."
        ),
        correct_conclusion="no_robust_edge",
        correct_root_cause="regime_dependent_signal",
        required_evidence_ids=("E-REGIME-WF", "E-REGIME-INF", "E-REGIME-STRESS"),
        required_tools=(
            "run_walk_forward_validation",
            "run_statistical_inference",
            "run_strategy_stress_test",
        ),
        tool_payloads={
            "inspect_market_context": {
                "status": "ok",
                "evidence_id": "E-REGIME-META",
                "target": "day-ahead German wind forecast error",
                "baseline": "persistence",
                "candidate": "weather-conditioned residual model",
                "split_policy": "chronological expanding window",
                "decision_metric": "net value after forecast-error-linked trading costs",
            },
            "run_data_quality_checks": {
                "status": "passed",
                "evidence_id": "E-REGIME-QUALITY",
                "duplicate_timestamps": 0,
                "missing_target_rows": 0,
                "future_feature_leakage": 0,
                "unit_check": "pass",
                "release_lag_check": "pass",
            },
            "run_walk_forward_validation": {
                "status": "mixed",
                "evidence_id": "E-REGIME-WF",
                "fold_net_value_change_pct": [1.2, -0.6, 0.9, -0.4, 0.6],
                "winning_folds": 3,
                "fold_count": 5,
                "pooled_net_value_change_pct": 0.34,
                "recent_holdout_net_value_change_pct": 0.1,
                "deterministic_verdict": "Small gains are unstable across time regimes.",
            },
            "run_statistical_inference": {
                "status": "not_significant",
                "evidence_id": "E-REGIME-INF",
                "estimator": "Newey-West HAC mean differential",
                "mean_net_value_change_pct": 0.34,
                "confidence_interval_95_pct": [-0.4, 1.0],
                "p_value": 0.36,
                "deterministic_verdict": (
                    "The interval includes zero; the data do not establish a reliable edge."
                ),
            },
            "run_strategy_stress_test": {
                "status": "failed",
                "evidence_id": "E-REGIME-STRESS",
                "base_cost_net_value_change_pct": 0.1,
                "double_cost_net_value_change_pct": -0.28,
                "high_volatility_net_value_change_pct": 0.04,
                "low_wind_regime_net_value_change_pct": -0.31,
                "deterministic_verdict": (
                    "The already small uplift turns negative under plausible cost and "
                    "low-wind stress."
                ),
            },
        },
    ),
}


def list_episodes() -> list[EpisodeSpec]:
    """Return independent copies so a run cannot mutate the registry."""

    return [deepcopy(episode) for episode in _EPISODES.values()]


def get_episode(episode_id: str) -> EpisodeSpec:
    try:
        return deepcopy(_EPISODES[episode_id])
    except KeyError as exc:
        known = ", ".join(sorted(_EPISODES))
        raise KeyError(f"Unknown episode {episode_id!r}. Choose one of: {known}") from exc
