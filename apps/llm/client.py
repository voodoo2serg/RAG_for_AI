import logging
import time
from typing import Optional, Dict, Any
from functools import wraps
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)

try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

try:
    from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
    HAS_TENACITY = True
except ImportError:
    HAS_TENACITY = False

try:
    import pybreaker
    HAS_PYBREAKER = True
except ImportError:
    HAS_PYBREAKER = False


# Circuit breaker configuration
CIRCUIT_BREAKER_CONFIG = {
    "fail_max": 5,
    "reset_timeout": 60,
}


class CircuitBreaker:
    """Simple circuit breaker implementation (fallback if pybreaker not installed)."""

    def __init__(self, fail_max=5, reset_timeout=60):
        self.fail_max = fail_max
        self.reset_timeout = reset_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func, *args, **kwargs):
        if self.state == "open":
            if time.time() - self.last_failure_time > self.reset_timeout:
                self.state = "half-open"
                logger.info("Circuit breaker entering half-open state")
            else:
                raise Exception("Circuit breaker is OPEN")

        try:
            result = func(*args, **kwargs)
            if self.state == "half-open":
                self.state = "closed"
                self.failure_count = 0
                logger.info("Circuit breaker closed")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            if self.failure_count >= self.fail_max:
                self.state = "open"
                logger.error(f"Circuit breaker OPENED after {self.failure_count} failures")
            raise


class LLMClient:
    """Client for LLM API (OpenAI-compatible) with resilience features:
    - Retry with exponential backoff
    - Circuit breaker
    - Fallback to secondary provider
    - Graceful degradation
    - Request timeout
    """

    def __init__(self):
        self.primary_client = None
        self.fallback_client = None
        self.model = getattr(settings, "LLM_MODEL", "gpt-4o-mini")
        self.max_tokens = getattr(settings, "LLM_MAX_TOKENS", 2048)
        self.temperature = getattr(settings, "LLM_TEMPERATURE", 0.7)
        self.request_timeout = getattr(settings, "LLM_REQUEST_TIMEOUT", 30)
        self.max_retries = getattr(settings, "LLM_MAX_RETRIES", 3)

        # Initialize circuit breaker
        if HAS_PYBREAKER:
            self.circuit_breaker = pybreaker.CircuitBreaker(**CIRCUIT_BREAKER_CONFIG)
        else:
            self.circuit_breaker = CircuitBreaker(**CIRCUIT_BREAKER_CONFIG)

        # Initialize primary client
        self._init_primary_client()
        # Initialize fallback client
        self._init_fallback_client()

    def _init_primary_client(self):
        """Initialize primary LLM client."""
        if HAS_OPENAI and getattr(settings, "OPENAI_API_KEY", ""):
            base_url = getattr(settings, "LLM_BASE_URL", None)
            kwargs = {"api_key": settings.OPENAI_API_KEY}
            if base_url:
                kwargs["base_url"] = base_url
            try:
                self.primary_client = OpenAI(**kwargs)
                logger.info("Primary LLM client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize primary LLM client: {e}")

    def _init_fallback_client(self):
        """Initialize fallback LLM client (secondary provider)."""
        fallback_key = getattr(settings, "FALLBACK_OPENAI_API_KEY", "")
        fallback_url = getattr(settings, "FALLBACK_LLM_BASE_URL", None)
        
        if HAS_OPENAI and fallback_key:
            kwargs = {"api_key": fallback_key}
            if fallback_url:
                kwargs["base_url"] = fallback_url
            try:
                self.fallback_client = OpenAI(**kwargs)
                logger.info("Fallback LLM client initialized")
            except Exception as e:
                logger.error(f"Failed to initialize fallback LLM client: {e}")

    def is_available(self) -> bool:
        return self.primary_client is not None or self.fallback_client is not None

    def _call_with_retry(self, client, messages: list, model: Optional[str] = None,
                         temperature: Optional[float] = None,
                         max_tokens: Optional[int] = None) -> Optional[str]:
        """Call LLM with retry logic."""
        
        def _make_request():
            response = client.chat.completions.create(
                model=model or self.model,
                messages=messages,
                temperature=temperature if temperature is not None else self.temperature,
                max_tokens=max_tokens if max_tokens is not None else self.max_tokens,
                timeout=self.request_timeout,
            )
            return response.choices[0].message.content

        if HAS_TENACITY:
            @retry(
                stop=stop_after_attempt(self.max_retries),
                wait=wait_exponential(multiplier=1, min=2, max=10),
                retry=retry_if_exception_type(Exception),
                reraise=True,
            )
            def _retry_request():
                return _make_request()
            
            return _retry_request()
        else:
            # Simple retry without tenacity
            last_error = None
            for attempt in range(self.max_retries):
                try:
                    return _make_request()
                except Exception as e:
                    last_error = e
                    wait_time = min(2 ** attempt, 10)
                    logger.warning(f"LLM call attempt {attempt + 1} failed: {e}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
            
            logger.error(f"LLM call failed after {self.max_retries} attempts: {last_error}")
            raise last_error

    def chat(
        self,
        messages: list,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> Optional[str]:
        """Send chat completion request with resilience features."""
        if not self.is_available():
            logger.warning("LLM client not available (missing API keys)")
            return self._get_cached_response(messages) or self._get_fallback_response(messages)

        # Try primary client with circuit breaker
        if self.primary_client:
            try:
                result = self.circuit_breaker.call(
                    self._call_with_retry,
                    self.primary_client,
                    messages,
                    model,
                    temperature,
                    max_tokens,
                )
                self._cache_response(messages, result)
                return result
            except Exception as e:
                logger.error(f"Primary LLM failed: {e}")

        # Try fallback client
        if self.fallback_client:
            try:
                logger.info("Trying fallback LLM provider...")
                result = self._call_with_retry(
                    self.fallback_client,
                    messages,
                    model,
                    temperature,
                    max_tokens,
                )
                self._cache_response(messages, result)
                return result
            except Exception as e:
                logger.error(f"Fallback LLM failed: {e}")

        # Graceful degradation
        return self._get_cached_response(messages) or self._get_fallback_response(messages)

    def _get_cached_response(self, messages: list) -> Optional[str]:
        """Get cached response if available."""
        cache_key = self._get_cache_key(messages)
        cached = cache.get(cache_key)
        if cached:
            logger.info("Returning cached LLM response")
            return cached
        return None

    def _cache_response(self, messages: list, response: str, timeout: int = 3600):
        """Cache successful response."""
        cache_key = self._get_cache_key(messages)
        cache.set(cache_key, response, timeout=timeout)

    def _get_cache_key(self, messages: list) -> str:
        """Generate cache key from messages."""
        import hashlib
        content = "".join([m.get("content", "") for m in messages])
        return f"llm:cache:{hashlib.md5(content.encode()).hexdigest()}"

    def _get_fallback_response(self, messages: list) -> Optional[str]:
        """Return fallback response when all LLM providers fail."""
        user_message = messages[-1].get("content", "") if messages else ""
        
        # Simple keyword-based fallback
        if any(kw in user_message.lower() for kw in ["error", "fail", "broken"]):
            return "I'm experiencing technical difficulties. Please try again in a few moments."
        
        return "I'm temporarily unavailable. Please try again shortly."

    def respond_with_rag(
        self,
        user_query: str,
        context_text: str,
        system_prompt: str = "",
        model: Optional[str] = None,
    ) -> tuple:
        """Generate RAG response with full resilience."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        if context_text:
            messages.append({"role": "system", "content": f"Use the following context to answer:\n\n{context_text}"})
        messages.append({"role": "user", "content": user_query})

        start = time.time()
        response_text = self.chat(messages, model=model)
        latency_ms = int((time.time() - start) * 1000)
        
        if response_text is None:
            response_text = self._get_fallback_response(messages)
        
        return response_text, latency_ms

    def get_health_status(self) -> Dict[str, Any]:
        """Return health status of LLM clients."""
        return {
            "primary_available": self.primary_client is not None,
            "fallback_available": self.fallback_client is not None,
            "circuit_breaker_state": getattr(self.circuit_breaker, "state", "unknown"),
            "model": self.model,
            "max_tokens": self.max_tokens,
        }


def get_llm_client() -> LLMClient:
    return LLMClient()
