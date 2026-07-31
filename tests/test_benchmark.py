from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from power_research_agent.benchmark import SuiteValidationError, load_sealed_suite


def _write_suite(tmp_path: Path) -> tuple[Path, Path, Path]:
    payloads = {
        name: {"status": "ok", "evidence_id": f"E-{index}"}
        for index, name in enumerate(
            (
                "inspect_market_context",
                "run_data_quality_checks",
                "run_walk_forward_validation",
                "run_statistical_inference",
                "run_strategy_stress_test",
            ),
            start=1,
        )
    }
    visible = {
        "suite_id": "sealed-test",
        "episodes": [
            {
                "episode_id": "case-1",
                "title": "A case",
                "question": "What happened?",
                "briefing": "Use all five audit gates.",
                "tool_payloads": payloads,
            }
        ],
    }
    answers = {
        "suite_id": "sealed-test",
        "answers": [
            {
                "episode_id": "case-1",
                "correct_conclusion": "repair_required",
                "correct_root_cause": "forecast_vintage_leakage",
                "required_evidence_ids": ["E-1", "E-2", "E-3", "E-4", "E-5"],
                "required_tools": list(payloads),
            }
        ],
    }
    episodes_path = tmp_path / "episodes.json"
    answers_path = tmp_path / "answers.json"
    episodes_path.write_text(json.dumps(visible), encoding="utf-8")
    answers_path.write_text(json.dumps(answers), encoding="utf-8")
    preregistration_path = tmp_path / "preregistration.json"
    preregistration_path.write_text(
        json.dumps(
            {
                "artifacts": {
                    "episodes_sha256": hashlib.sha256(episodes_path.read_bytes()).hexdigest(),
                    "answers_sha256": hashlib.sha256(answers_path.read_bytes()).hexdigest(),
                }
            }
        ),
        encoding="utf-8",
    )
    return episodes_path, answers_path, preregistration_path


def test_load_sealed_suite_joins_visible_case_to_answer_key(tmp_path: Path) -> None:
    episodes_path, answers_path, preregistration_path = _write_suite(tmp_path)

    suite = load_sealed_suite(
        episodes_path,
        answers_path,
        preregistration_path=preregistration_path,
    )

    assert suite.suite_id == "sealed-test"
    assert suite.episodes[0].correct_root_cause == "forecast_vintage_leakage"
    assert "forecast_vintage_leakage" not in suite.episodes[0].model_prompt()


def test_load_sealed_suite_rejects_hash_drift(tmp_path: Path) -> None:
    episodes_path, answers_path, preregistration_path = _write_suite(tmp_path)
    episodes_path.write_text(episodes_path.read_text() + "\n", encoding="utf-8")

    with pytest.raises(SuiteValidationError, match="hash"):
        load_sealed_suite(
            episodes_path,
            answers_path,
            preregistration_path=preregistration_path,
        )


def test_load_sealed_suite_rejects_visible_answer_leakage(tmp_path: Path) -> None:
    episodes_path, answers_path, _ = _write_suite(tmp_path)
    visible = json.loads(episodes_path.read_text())
    visible["episodes"][0]["correct_conclusion"] = "repair_required"
    episodes_path.write_text(json.dumps(visible), encoding="utf-8")

    with pytest.raises(SuiteValidationError, match="leaks answer fields"):
        load_sealed_suite(episodes_path, answers_path)
