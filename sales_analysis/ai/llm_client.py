import json
import os
import socket
import urllib.error
import urllib.request

from sales_analysis.project_paths import ProjectPaths


class EnvironmentLoader:
    def __init__(self, env_path=".env"):
        self.env_path = ProjectPaths.resolve(env_path)

    def load(self):
        if not self.env_path.exists():
            return

        for line in self.env_path.read_text(encoding="utf-8").splitlines():
            self.load_line(line)

    @staticmethod
    def load_line(line):
        stripped_line = line.strip()
        if not stripped_line or stripped_line.startswith("#"):
            return

        if "=" not in stripped_line:
            return

        key, value = stripped_line.split("=", 1)
        clean_key = key.strip()
        clean_value = value.strip().strip('"').strip("'")
        if clean_key and clean_key not in os.environ:
            os.environ[clean_key] = clean_value


class StreamlitSecrets:
    @staticmethod
    def value(name):
        try:
            import streamlit as st
        except Exception:
            return None

        try:
            secret_value = st.secrets.get(name)
        except Exception:
            return None

        if secret_value is None:
            return None

        return str(secret_value)


class LLMClient:
    api_key_env = "OPENAI_API_KEY"
    endpoint_env = "OPENAI_API_URL"
    model_env = "OPENAI_MODEL"
    timeout_env = "OPENAI_TIMEOUT_SECONDS"
    max_tokens_env = "OPENAI_MAX_TOKENS"
    minimum_completion_tokens = 1200

    def __init__(self, api_key="", endpoint="", model=""):
        EnvironmentLoader().load()
        self.api_key = api_key or self.setting(self.api_key_env)
        self.endpoint = endpoint or self.setting(self.endpoint_env)
        self.model = model or self.setting(self.model_env)
        self.timeout_seconds = self.optional_number_from_setting(
            self.timeout_env,
            "OpenAI timeout must be a number.",
        )
        self.max_tokens = self.optional_number_from_setting(
            self.max_tokens_env,
            "OpenAI max tokens must be a number.",
        )

    def ask(self, prompt):
        self.validate_request(prompt)
        self.ensure_request_limits()
        data = self.send_request(self.request(prompt))
        return self.response_text(data)

    def validate_request(self, prompt):
        """Fail before network calls when required OpenAI settings are missing."""

        if not self.api_key:
            raise ValueError("Missing OpenAI API key.")

        if not self.endpoint:
            raise ValueError("Missing OpenAI API URL.")

        if not self.model:
            raise ValueError("Missing OpenAI model.")

        if not prompt.strip():
            raise ValueError("Prompt cannot be empty.")

    def ensure_request_limits(self):
        if self.timeout_seconds is None:
            self.timeout_seconds = self.timeout()

        if self.max_tokens is None:
            self.max_tokens = self.response_token_limit()

        self.max_tokens = max(self.max_tokens, self.minimum_completion_tokens)

    def request(self, prompt):
        return urllib.request.Request(
            self.endpoint,
            data=json.dumps(self.payload(prompt)).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

    def send_request(self, request):
        """Send the HTTP request and normalize transport errors as ValueError."""

        try:
            with urllib.request.urlopen(
                request,
                timeout=self.timeout_seconds,
            ) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as error:
            raise ValueError(error.read().decode("utf-8")) from error
        except urllib.error.URLError as error:
            raise ValueError(str(error.reason)) from error
        except socket.timeout as error:
            raise ValueError("OpenAI request timed out.") from error

    def payload(self, prompt):
        return {
            "model": self.model,
            "max_completion_tokens": self.max_tokens,
            "stream": False,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a concise sales analytics assistant. "
                        "Answer in at most 80 words, using no more than 3 "
                        "bullets. No preamble."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        }

    @staticmethod
    def response_text(data):
        message = data["choices"][0]["message"]
        content = message.get("content")
        if isinstance(content, str) and content.strip():
            return content

        if isinstance(content, list):
            text_parts = [
                item.get("text", "")
                for item in content
                if isinstance(item, dict)
            ]
            text = "".join(text_parts).strip()
            if text:
                return text

        finish_reason = data["choices"][0].get("finish_reason")
        if finish_reason == "length":
            raise ValueError(
                "OpenAI returned no visible answer text because the completion "
                "token limit was exhausted. Increase OPENAI_MAX_TOKENS in "
                "Streamlit secrets."
            )

        raise ValueError("OpenAI response did not include visible answer text.")

    @classmethod
    def timeout(cls):
        timeout_value = cls.setting(cls.timeout_env)
        if not timeout_value:
            raise ValueError("Missing OpenAI timeout.")

        return cls.number_from_env(
            timeout_value,
            "OpenAI timeout must be a number.",
        )

    @classmethod
    def response_token_limit(cls):
        max_tokens_value = cls.setting(cls.max_tokens_env)
        if not max_tokens_value:
            raise ValueError("Missing OpenAI max tokens.")

        return cls.number_from_env(
            max_tokens_value,
            "OpenAI max tokens must be a number.",
        )

    @staticmethod
    def number_from_env(value, message):
        try:
            return int(value)
        except ValueError as error:
            raise ValueError(message) from error

    @classmethod
    def setting(cls, name):
        return os.getenv(name) or StreamlitSecrets.value(name)

    @classmethod
    def optional_number_from_setting(cls, name, message):
        value = cls.setting(name)
        if not value:
            return None

        return cls.number_from_env(value, message)
