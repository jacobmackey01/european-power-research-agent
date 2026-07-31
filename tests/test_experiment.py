from __future__ import annotations

from power_research_agent.experiment import assess_claims


def test_assess_claims_enforces_compaction_activation_gate() -> None:
    comparisons = {
        "compaction": {
            "complete": True,
            "compaction_activation": {"rate": 0.5},
            "metrics": {
                "score": {
                    "delta": 1.0,
                    "delta_ci_95": [-1.0, 3.0],
                    "two_sided_sign_flip_p": 0.5,
                }
            },
        }
    }
    rules = [
        {
            "name": "quality_preserved",
            "comparison": "compaction",
            "metric": "score",
            "kind": "noninferiority",
            "margin": 5.0,
            "requires_compaction": True,
            "minimum_compaction_activation_rate": 0.8,
        }
    ]

    result = assess_claims(comparisons, rules)

    assert result["quality_preserved"]["status"] == "not_testable"
