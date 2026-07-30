from __future__ import annotations

import json
from types import SimpleNamespace
from typing import Any


def function_call_response(
    response_id: str,
    name: str,
    arguments: dict[str, Any],
    *,
    call_id: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=response_id,
        output=[
            SimpleNamespace(
                type="function_call",
                name=name,
                arguments=json.dumps(arguments),
                call_id=call_id or f"call-{response_id}",
            )
        ],
        output_text="",
        usage=SimpleNamespace(
            input_tokens=10,
            output_tokens=5,
            total_tokens=15,
            input_tokens_details=SimpleNamespace(
                cached_tokens=2,
                cache_write_tokens=1,
            ),
            output_tokens_details=SimpleNamespace(reasoning_tokens=3),
        ),
    )


class FakeResponses:
    def __init__(self, scripted: list[SimpleNamespace]) -> None:
        self.scripted = list(scripted)
        self.requests: list[dict[str, Any]] = []

    def create(self, **kwargs: Any) -> SimpleNamespace:
        self.requests.append(kwargs)
        if not self.scripted:
            raise AssertionError("No scripted response remains.")
        return self.scripted.pop(0)


class FakeClient:
    def __init__(self, scripted: list[SimpleNamespace]) -> None:
        self.responses = FakeResponses(scripted)
