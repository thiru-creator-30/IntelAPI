from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


@dataclass
class LLMResult:
    ok: bool
    text: str | None = None
    error: str | None = None
    meta: dict[str, Any] | None = None


class LLMProvider(Protocol):
    name: str

    async def complete(self, prompt: str, *, max_tokens: int = 500, temperature: float = 0.2) -> LLMResult: ...
