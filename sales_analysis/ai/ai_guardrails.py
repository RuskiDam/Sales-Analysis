class AIGuardrails:
    max_prompt_chars = 1000
    blocked_phrase_groups = {
        "secrets": [
            ".env",
            "api key",
            "openai_api_key",
            "llm_api_key",
            "secret",
            "confidential",
        ],
        "source_access": [
            "source code",
            "read file",
            "list files",
            "show files",
            "leak",
        ],
        "mutation": [
            "delete",
            "overwrite",
            "modify inventory",
            "change inventory",
            "edit sales",
            "reset data",
        ],
        "prompt_injection": [
            "<instruction",
            "</instruction",
            "<system",
            "</system",
            "<developer",
            "</developer",
            "<prompt",
            "</prompt",
            "ignore previous instructions",
            "disregard",
            "disregard filters",
            "ignore filters",
            "remove filters",
            "disable filters",
            "turn off filters",
            "bypass",
            "jailbreak",
            "roleplay",
            "pretend",
            "act as",
            "you are now",
            "developer mode",
            "dan mode",
            "evil assistant",
            "no restrictions",
            "without restrictions",
            "forget your instructions",
            "reveal your instructions",
            "system prompt",
            "hidden prompt",
        ],
        "off_topic_entertainment": [
            "riddle",
            "joke",
            "funny",
            "song",
            "music",
            "lyrics",
            "poem",
            "rap",
            "sing",
            "melody",
        ],
    }

    def validate(self, prompt):
        """Normalize a user prompt and reject blocked A.I. request categories."""

        cleaned_prompt = prompt.strip()
        if not cleaned_prompt:
            raise ValueError("Prompt cannot be empty.")

        if len(cleaned_prompt) > self.max_prompt_chars:
            raise ValueError("Prompt is too long.")

        violation = self.blocked_violation(cleaned_prompt)
        if violation:
            raise ValueError(f"That request is not allowed: {violation}.")

        return cleaned_prompt

    @classmethod
    def blocked_violation(cls, prompt):
        lowered_prompt = prompt.lower()
        for group_name, phrases in cls.blocked_phrase_groups.items():
            matches = [
                phrase for phrase in phrases if phrase in lowered_prompt
            ]
            if matches:
                return group_name.replace("_", " ")

        return ""


class GuardrailDependencyLoader:
    @staticmethod
    def load_component():
        try:
            from haystack import component
        except ImportError as error:
            raise ValueError(
                "Haystack guardrail dependency is missing. "
                "Install requirements.txt first."
            ) from error

        return component


class GuardrailComponentFactory:
    """Wraps app guardrails in a Haystack component for the RAG pipeline."""

    @staticmethod
    def create(guardrails=None, component=None):
        """Create a Haystack component that validates prompts before embedding."""

        haystack_component = (
            component or GuardrailDependencyLoader.load_component()
        )
        validator = guardrails or AIGuardrails()

        @haystack_component
        class GuardrailComponent:
            @haystack_component.output_types(prompt=str)
            def run(self, prompt):
                return {"prompt": validator.validate(prompt)}

        return GuardrailComponent()
