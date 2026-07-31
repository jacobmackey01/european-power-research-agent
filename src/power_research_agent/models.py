from __future__ import annotations

from dataclasses import asdict, dataclass, field, is_dataclass
from enum import Enum, StrEnum
from typing import Any


class HarnessMode(StrEnum):
    """Conversation-memory condition used for an experiment run."""

    STATELESS_TRUNCATED = "stateless-truncated"
    RETAINED_REASONING = "retained-reasoning"
    RETAINED_REASONING_COMPACTION = "retained-reasoning-compaction"


CONCLUSIONS = (
    "repair_required",
    "no_robust_edge",
    "provisional_signal",
)

ROOT_CAUSES = (
    "dst_duplicate_local_hour",
    "unit_scale_shift_gw_as_mw",
    "regime_dependent_signal",
    "timezone_alignment_error",
    "forecast_vintage_leakage",
    "structural_break",
    "missing_not_at_random_outages",
    "insufficient_evidence",
)


@dataclass(frozen=True)
class EpisodeSpec:
    """A deterministic public development episode plus its evaluator labels."""

    episode_id: str
    title: str
    question: str
    briefing: str
    correct_conclusion: str
    correct_root_cause: str
    required_evidence_ids: tuple[str, ...]
    required_tools: tuple[str, ...]
    tool_payloads: dict[str, dict[str, Any]]

    def model_prompt(self) -> str:
        """Render model-visible fields only; answer-key fields are excluded."""

        return (
            f"Episode: {self.episode_id}\n"
            f"Title: {self.title}\n\n"
            f"Research question:\n{self.question}\n\n"
            f"Initial briefing:\n{self.briefing}\n\n"
            "Investigate with the available tools. Your terminal action must be "
            "submit_research_memo."
        )


@dataclass
class AgentReport:
    conclusion: str
    root_cause: str
    evidence_ids: list[str]
    summary: str
    risk_assessment: str


@dataclass
class ToolEvent:
    step: int
    tool_name: str
    arguments: dict[str, Any]
    result: dict[str, Any]
    duplicate: bool = False


@dataclass
class UsageTotals:
    input_tokens: int = 0
    cached_input_tokens: int = 0
    cache_write_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    total_tokens: int = 0


@dataclass
class RunResult:
    episode_id: str
    mode: str
    model: str
    reasoning_effort: str
    report: AgentReport | None
    tool_events: list[ToolEvent]
    usage: UsageTotals
    response_ids: list[str] = field(default_factory=list)
    response_models: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0
    compact_threshold: int | None = None
    compaction_events: int = 0
    effective_reasoning_contexts: list[str] = field(default_factory=list)
    service_tiers: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return json_ready(self)


@dataclass
class RunScore:
    episode_id: str
    total: float
    components: dict[str, float]
    exact_success: bool
    diagnostics: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return json_ready(self)


def json_ready(value: Any) -> Any:
    """Recursively convert dataclasses and enums into JSON-compatible values."""

    if is_dataclass(value):
        return {key: json_ready(item) for key, item in asdict(value).items()}
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): json_ready(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_ready(item) for item in value]
    return value
