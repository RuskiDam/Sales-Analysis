from sales_analysis.ai.ai_context import AIContextBuilder
from sales_analysis.ai.llm_client import LLMClient
from sales_analysis.ai.rag_pipeline import HaystackRAGPipeline
from sales_analysis.ai.skill_loader import SkillLoader


class AIService:
    client_error_prefix = "A.I. request failed:"
    max_history_messages = 6
    max_history_chars = 1200

    def __init__(
        self,
        data_store,
        metrics,
        finance_policy,
        llm_client=None,
        context_builder=None,
        skill_loader=None,
        rag_pipeline=None,
    ):
        self.llm_client = llm_client
        self.context_builder = context_builder or AIContextBuilder(
            data_store,
            metrics,
            finance_policy,
        )
        self.skill_loader = skill_loader or SkillLoader()
        self.rag_pipeline = rag_pipeline

    def answer(self, prompt, model, chat_history=None):
        """Validate API readiness, run RAG, and return a display-ready result."""

        client = self.llm_client or LLMClient(model=model)
        if not client.api_key:
            raise ValueError("Missing OpenAI API key.")

        try:
            rag_pipeline = self.rag_pipeline or HaystackRAGPipeline()
            rag_result = rag_pipeline.answer(
                prompt,
                client,
                self.grounded_prompt(prompt, chat_history),
            )
            return rag_result
        except ValueError as error:
            raise ValueError(f"{self.client_error_prefix} {error}") from error
        except Exception as error:
            raise ValueError(
                f"{self.client_error_prefix} "
                "RAG retrieval failed while processing the question."
            ) from error

    def grounded_prompt(self, prompt, chat_history=None):
        return (
            f"SKILL:\n{self.skill_loader.load()}\n\n"
            f"APP CONTEXT:\n{self.context_builder.build()}\n\n"
            f"RECENT CHAT:\n{self.chat_context(chat_history)}\n\n"
            f"USER QUESTION:\n{prompt}"
        )

    @classmethod
    def chat_context(cls, chat_history=None):
        if not chat_history:
            return "No prior chat."

        lines = []
        for message in chat_history[-cls.max_history_messages:]:
            role = message.get("role", "unknown")
            content = message.get("content", "").strip()
            if content:
                lines.append(f"{role}: {content}")

        text = "\n".join(lines).strip()
        if not text:
            return "No prior chat."

        return text[-cls.max_history_chars:]
