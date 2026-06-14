import os
import socket
import unittest
from unittest.mock import patch

from sales_analysis.ai.llm_client import (
    EnvironmentLoader,
    LLMClient,
    StreamlitSecrets,
)


class LLMClientTest(unittest.TestCase):
    test_endpoint = "https://example.test/v1/chat/completions"
    test_model = "custom/model"

    def client(self, **overrides):
        environment = {
            "OPENAI_TIMEOUT_SECONDS": "30",
            "OPENAI_MAX_TOKENS": "800",
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch.object(EnvironmentLoader, "load"):
                return LLMClient(**overrides)

    def test_project_env_model(self):
        client = LLMClient()
        self.assertEqual(client.model, "gpt-5.5")

    def test_missing_endpoint_fails(self):
        with self.assertRaises(ValueError):
            self.client(
                api_key="test-key",
                model=self.test_model,
            ).ask("What is revenue?")

    def test_env_overrides_defaults(self):
        environment = {
            "OPENAI_API_KEY": "openai-key",
            "OPENAI_API_URL": self.test_endpoint,
            "OPENAI_MODEL": "custom/openai-model",
            "OPENAI_TIMEOUT_SECONDS": "45",
            "OPENAI_MAX_TOKENS": "250",
        }
        with patch.dict(os.environ, environment, clear=True):
            with patch.object(EnvironmentLoader, "load"):
                client = LLMClient()
            self.assertEqual(client.api_key, "openai-key")
            self.assertEqual(client.endpoint, environment["OPENAI_API_URL"])
            self.assertEqual(client.model, "custom/openai-model")
            self.assertEqual(client.timeout_seconds, 45)
            self.assertEqual(client.max_tokens, 250)

    def test_streamlit_secrets_fill_missing_settings(self):
        secrets = {
            "OPENAI_API_KEY": "streamlit-key",
            "OPENAI_API_URL": self.test_endpoint,
            "OPENAI_MODEL": self.test_model,
            "OPENAI_TIMEOUT_SECONDS": "35",
            "OPENAI_MAX_TOKENS": "300",
        }
        with patch.dict(os.environ, {}, clear=True):
            with patch.object(EnvironmentLoader, "load"):
                with patch.object(StreamlitSecrets, "value", side_effect=secrets.get):
                    client = LLMClient()

        self.assertEqual(client.api_key, "streamlit-key")
        self.assertEqual(client.endpoint, self.test_endpoint)
        self.assertEqual(client.model, self.test_model)
        self.assertEqual(client.timeout_seconds, 35)
        self.assertEqual(client.max_tokens, 300)

    def test_chat_payload_shape(self):
        client = self.client(
            api_key="test-key",
            endpoint=self.test_endpoint,
            model=self.test_model,
        )
        payload = client.payload("What is revenue?")
        self.assertEqual(payload["model"], self.test_model)
        self.assertEqual(payload["max_tokens"], client.max_tokens)
        self.assertEqual(payload["stream"], False)
        self.assertEqual(payload["messages"][1]["content"], "What is revenue?")

    def test_timeout_error(self):
        client = self.client(
            api_key="test-key",
            endpoint=self.test_endpoint,
            model=self.test_model,
        )

        with patch("urllib.request.urlopen", side_effect=socket.timeout):
            with self.assertRaises(ValueError):
                client.ask("What is revenue?")

    def test_missing_content_fails(self):
        data = {"choices": [{"message": {"role": "assistant"}}]}
        with self.assertRaises(ValueError):
            LLMClient.response_text(data)


if __name__ == "__main__":
    unittest.main()
