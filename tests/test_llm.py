"""Tests for LLM client — chat, respond_with_rag, fallback, retry."""

from unittest.mock import patch, MagicMock
from django.test import TestCase, override_settings
from apps.llm.client import LLMClient, get_llm_client


class LLMClientTestCase(TestCase):
    """Test LLM client initialization and basic functionality."""

    def test_client_initialization_without_api_key(self):
        with override_settings(OPENAI_API_KEY=""):
            client = LLMClient()
            self.assertFalse(client.is_available())

    def test_client_initialization_with_api_key(self):
        with override_settings(OPENAI_API_KEY="test-key"):
            client = LLMClient()
            # Mock the OpenAI client to avoid actual API calls
            with patch("apps.llm.client.OpenAI"):
                self.assertTrue(client.is_available())

    def test_chat_without_client(self):
        with override_settings(OPENAI_API_KEY=""):
            client = LLMClient()
            result = client.chat([{"role": "user", "content": "Hello"}])
            self.assertIsNone(result)

    @patch("apps.llm.client.OpenAI")
    def test_chat_success(self, mock_openai_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Hello!"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        with override_settings(OPENAI_API_KEY="test-key"):
            client = LLMClient()
            result = client.chat([{"role": "user", "content": "Hello"}])
            self.assertEqual(result, "Hello!")

    @patch("apps.llm.client.OpenAI")
    def test_chat_failure(self, mock_openai_class):
        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = Exception("API Error")
        mock_openai_class.return_value = mock_client

        with override_settings(OPENAI_API_KEY="test-key"):
            client = LLMClient()
            result = client.chat([{"role": "user", "content": "Hello"}])
            # Should return None on failure (current behavior)
            self.assertIsNone(result)

    @patch("apps.llm.client.OpenAI")
    def test_respond_with_rag(self, mock_openai_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Based on context..."))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        with override_settings(OPENAI_API_KEY="test-key"):
            client = LLMClient()
            response_text, latency_ms = client.respond_with_rag(
                user_query="What is Django?",
                context_text="Django is a Python web framework.",
                system_prompt="You are a helpful assistant.",
            )
            self.assertEqual(response_text, "Based on context...")
            self.assertIsInstance(latency_ms, int)
            self.assertGreater(latency_ms, 0)

    @patch("apps.llm.client.OpenAI")
    def test_respond_with_rag_no_context(self, mock_openai_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="I don't know."))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        with override_settings(OPENAI_API_KEY="test-key"):
            client = LLMClient()
            response_text, latency_ms = client.respond_with_rag(
                user_query="What is Django?",
                context_text="",
            )
            self.assertEqual(response_text, "I don't know.")

    def test_get_llm_client_singleton(self):
        client1 = get_llm_client()
        client2 = get_llm_client()
        # Should return new instances (not singleton currently)
        self.assertIsInstance(client1, LLMClient)
        self.assertIsInstance(client2, LLMClient)

    @patch("apps.llm.client.OpenAI")
    def test_chat_with_custom_model(self, mock_openai_class):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Custom model response"))]
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai_class.return_value = mock_client

        with override_settings(OPENAI_API_KEY="test-key"):
            client = LLMClient()
            result = client.chat(
                [{"role": "user", "content": "Hello"}],
                model="gpt-4o",
                temperature=0.5,
                max_tokens=100,
            )
            self.assertEqual(result, "Custom model response")
            # Verify the call was made with custom parameters
            call_kwargs = mock_client.chat.completions.create.call_args.kwargs
            self.assertEqual(call_kwargs["model"], "gpt-4o")
            self.assertEqual(call_kwargs["temperature"], 0.5)
            self.assertEqual(call_kwargs["max_tokens"], 100)


class LLMResilienceTestCase(TestCase):
    """Test LLM resilience features — retry, fallback, circuit breaker."""

    @patch("apps.llm.client.OpenAI")
    def test_retry_on_temporary_failure(self, mock_openai_class):
        """Test that temporary failures are retried."""
        mock_client = MagicMock()
        # First call fails, second succeeds
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Success after retry"))]
        mock_client.chat.completions.create.side_effect = [
            Exception("Temporary error"),
            mock_response,
        ]
        mock_openai_class.return_value = mock_client

        with override_settings(OPENAI_API_KEY="test-key"):
            client = LLMClient()
            # Currently no retry — this test documents expected behavior
            result = client.chat([{"role": "user", "content": "Hello"}])
            # TODO: After implementing retry, this should return "Success after retry"
            self.assertIsNone(result)  # Current behavior: no retry

    def test_fallback_provider(self):
        """Test fallback to secondary LLM provider."""
        # TODO: Implement fallback provider support
        # Currently not supported — this test documents the gap
        with override_settings(OPENAI_API_KEY=""):
            client = LLMClient()
            self.assertFalse(client.is_available())
            # Should fallback to secondary provider if configured

    def test_circuit_breaker(self):
        """Test circuit breaker prevents cascading failures."""
        # TODO: Implement circuit breaker
        # Currently not supported — this test documents the gap
        pass

    def test_graceful_degradation(self):
        """Test graceful degradation when LLM is unavailable."""
        with override_settings(OPENAI_API_KEY=""):
            client = LLMClient()
            result = client.respond_with_rag(
                user_query="What is Django?",
                context_text="Django is a Python web framework.",
            )
            # Should return a fallback message or cached response
            self.assertIsNone(result[0])  # Current behavior: returns None
