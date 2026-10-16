from __future__ import annotations

import os
from typing import Any

from app.core.config import get_settings
from app.core.logging import get_logger
from app.integrations.llm.base import LLMResult
from app.execution.service import PreparedRequest, execute as secure_execute

log = get_logger(__name__)


class OpenAICompatProvider:
    name = "openai-compat"

    def __init__(self) -> None:
        s = get_settings()
        self.api_key = os.getenv("LLM_API_KEY", "")
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-4o-mini")
        self._enabled = bool(self.api_key)

    async def complete(self, prompt: str, *, max_tokens: int = 500, temperature: float = 0.2) -> LLMResult:
        if not self._enabled:
            return LLMResult(ok=False, error="LLM not configured")
        if len(prompt) > 12000:
            prompt = prompt[:12000]
        import json
        body = json.dumps(
            {
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": temperature,
            }
        )
        pr = PreparedRequest(
            method="POST",
            url=self.base_url.rstrip("/") + "/chat/completions",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            body=body,
            secret_values=[self.api_key],
        )
        result = await secure_execute(pr)
        if result.outcome != "http_response" or not result.response_body_excerpt:
            return LLMResult(ok=False, error=f"LLM request failed: {result.outcome}")
        try:
            data = json.loads(result.response_body_excerpt)
            text = data["choices"][0]["message"]["content"]
            return LLMResult(ok=True, text=text, meta={"model": self.model})
        except Exception as exc:
            return LLMResult(ok=False, error=f"invalid LLM response: {type(exc).__name__}")


def get_llm_provider() -> OpenAICompatProvider:
    return OpenAICompatProvider()
