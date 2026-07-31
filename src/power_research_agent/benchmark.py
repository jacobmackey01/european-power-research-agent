from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from power_research_agent.environment import ANALYSIS_TOOLS
from power_research_agent.models import CONCLUSIONS, ROOT_CAUSES, EpisodeSpec

_ANSWER_FIELDS = {
    "correct_conclusion",
    "correct_root_cause",
    "required_evidence_ids",
    "required_tools",
}


@dataclass(frozen=True)
class SealedSuite:
    """Verified model-visible cases joined to an evaluator-only answer key."""

    suite_id: str
    episodes: tuple[EpisodeSpec, ...]
    episodes_sha256: str
    answers_sha256: str


class SuiteValidationError(ValueError):
    """Raised before any paid calls when a sealed suite fails validation."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_sealed_suite(
    episodes_path: Path,
    answers_path: Path,
    *,
    preregistration_path: Path | None = None,
) -> SealedSuite:
    """Load a suite and fail closed if files differ from preregistered hashes."""

    visible = _load_json_object(episodes_path)
    answers = _load_json_object(answers_path)
    episodes_hash = sha256_file(episodes_path)
    answers_hash = sha256_file(answers_path)

    if preregistration_path is not None:
        preregistration = _load_json_object(preregistration_path)
        artifacts = _object(preregistration.get("artifacts"), "artifacts")
        _check_hash("episodes", episodes_hash, artifacts.get("episodes_sha256"))
        _check_hash("answers", answers_hash, artifacts.get("answers_sha256"))

    suite_id = _text(visible.get("suite_id"), "visible suite_id")
    if _text(answers.get("suite_id"), "answer suite_id") != suite_id:
        raise SuiteValidationError("Visible suite and answer key have different suite IDs.")

    visible_rows = _object_list(visible.get("episodes"), "episodes")
    answer_rows = _object_list(answers.get("answers"), "answers")
    answer_by_id = _index_unique(answer_rows, "answer")
    visible_by_id = _index_unique(visible_rows, "episode")
    if set(visible_by_id) != set(answer_by_id):
        raise SuiteValidationError("Visible episode IDs and answer-key IDs do not match.")

    episodes: list[EpisodeSpec] = []
    for episode_id, row in visible_by_id.items():
        leaked = sorted(_ANSWER_FIELDS.intersection(row))
        if leaked:
            raise SuiteValidationError(
                f"Visible episode {episode_id!r} leaks answer fields: {', '.join(leaked)}."
            )
        answer = answer_by_id[episode_id]
        conclusion = _text(answer.get("correct_conclusion"), "correct_conclusion")
        root_cause = _text(answer.get("correct_root_cause"), "correct_root_cause")
        if conclusion not in CONCLUSIONS:
            raise SuiteValidationError(f"Unsupported conclusion in {episode_id!r}: {conclusion}")
        if root_cause not in ROOT_CAUSES:
            raise SuiteValidationError(f"Unsupported root cause in {episode_id!r}: {root_cause}")

        tool_payloads = _object(row.get("tool_payloads"), "tool_payloads")
        required_evidence_ids = tuple(
            _string_list(answer.get("required_evidence_ids"), "required_evidence_ids")
        )
        required_tools = tuple(_string_list(answer.get("required_tools"), "required_tools"))
        unsupported_tools = sorted(set(required_tools).difference(ANALYSIS_TOOLS))
        if unsupported_tools:
            raise SuiteValidationError(
                f"Unknown required tools in {episode_id!r}: {', '.join(unsupported_tools)}."
            )
        missing_payloads = sorted(set(ANALYSIS_TOOLS).difference(tool_payloads))
        if missing_payloads:
            raise SuiteValidationError(
                f"Episode {episode_id!r} lacks tool payloads: {', '.join(missing_payloads)}."
            )
        available_evidence = _evidence_ids(tool_payloads)
        missing_evidence = sorted(set(required_evidence_ids).difference(available_evidence))
        if missing_evidence:
            raise SuiteValidationError(
                f"Answer key for {episode_id!r} requires absent evidence: "
                f"{', '.join(missing_evidence)}."
            )

        episodes.append(
            EpisodeSpec(
                episode_id=episode_id,
                title=_text(row.get("title"), "title"),
                question=_text(row.get("question"), "question"),
                briefing=_text(row.get("briefing"), "briefing"),
                correct_conclusion=conclusion,
                correct_root_cause=root_cause,
                required_evidence_ids=required_evidence_ids,
                required_tools=required_tools,
                tool_payloads=tool_payloads,
            )
        )

    return SealedSuite(
        suite_id=suite_id,
        episodes=tuple(episodes),
        episodes_sha256=episodes_hash,
        answers_sha256=answers_hash,
    )


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SuiteValidationError(f"Could not load {path}: {exc}") from exc
    return _object(value, str(path))


def _check_hash(label: str, actual: str, expected: Any) -> None:
    if not isinstance(expected, str) or actual != expected:
        raise SuiteValidationError(
            f"{label.capitalize()} hash does not match the preregistration. "
            "Do not run paid evaluation calls."
        )


def _index_unique(rows: list[dict[str, Any]], label: str) -> dict[str, dict[str, Any]]:
    indexed: dict[str, dict[str, Any]] = {}
    for row in rows:
        episode_id = _text(row.get("episode_id"), f"{label} episode_id")
        if episode_id in indexed:
            raise SuiteValidationError(f"Duplicate {label} ID: {episode_id}")
        indexed[episode_id] = row
    if not indexed:
        raise SuiteValidationError(f"The {label} list is empty.")
    return indexed


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SuiteValidationError(f"{label} must be a JSON object.")
    return value


def _object_list(value: Any, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise SuiteValidationError(f"{label} must be a list of JSON objects.")
    return value


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SuiteValidationError(f"{label} must be a non-empty string.")
    return value


def _string_list(value: Any, label: str) -> list[str]:
    if not isinstance(value, list) or not value or not all(isinstance(item, str) for item in value):
        raise SuiteValidationError(f"{label} must be a non-empty list of strings.")
    if len(value) != len(set(value)):
        raise SuiteValidationError(f"{label} contains duplicates.")
    return value


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
