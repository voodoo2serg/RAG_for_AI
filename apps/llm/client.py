import logging
import time
from typing import Optional
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False


class LLMClient:
    """Client for LLM API (OpenAI-compatible)."""

    def __init__(self):
        self.client = None
        self.model = getattr(settings, "LLM_MODEL", "gpt-4o-mini")
        self.max_tokens = getattr(settings, "LLM_MAX_TOKENS", 2048)
        self.temperature = getattr(settings, "LLM_TEMPERATURE", 0.7)
        if HAS_OPENAI and getattr(settings, "OPENAI_API_KEY", ""):
            base_url = getattr(settings, "LLM_BASE_URL", None)
            kwargs = {"api_key": settings.OPENAI_API_KEY}
            if base_url:
                kwargs["base_url"] = base_url
            self.client = OpenAI(**kwargs)

    def is_available(self) -> bool:
        return self.client is not None

    def chat(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        if not self.client:
            logger.warning("LLM client not available (missing OPENAI_API_KEY)")
            return None
        try:
            start = time.time()
            response = self.client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
            )
            latency_ms = int((time.time() - start) * 1000)
            content = response.choices[0].message.content
            logger.info("LLM response generated in %dms, model=%s", latency_ms, model or self.model)
            return content
        except Exception as e:
            logger.error("LLM call failed: %s", e)
            return None

    def respond_with_rag(
        self,
        user_query: str,
        context_text: str,
        system_prompt: str = "",
        model: Optional[str] = None,
    ) -> tuple:
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context_text:
            messages.append({"role": "system", "content": f"Use the following context to answer:\n\n{context_text}"})
        messages.append({"role": "user", "content": user_query})

        start = time.time()
        response_text = self.chat(messages, model=model)
        latency_ms = int((time.time() - start) * 1000)
        return response_text, latency_ms


def get_llm_client() -> LLMClient:
    return LLMClient()
