import unittest

from sales_analysis.ai.rag_pipeline import RAGCorpus, RAGResult


class FakeDocument:
    def __init__(self, content, source):
        self.content = content
        self.meta = {"source": source}


class RAGResultTest(unittest.TestCase):
    def test_default_source(self):
        sources = [row["source"] for row in RAGCorpus().sources()]

        self.assertEqual(
            sources,
            [
                "docs/ai_skill_spec.md",
                "docs/business_baselines.md",
                "docs/finance_rules.md",
                "docs/inventory_policy.md",
                "docs/sales_terms.md",
            ],
        )

    def test_default_corpus_explains_data_access(self):
        documents = RAGCorpus().documents()
        content = "\n".join(document["content"] for document in documents)

        self.assertIn("Data Access Contract", content)
        self.assertIn("latest month revenue", content)
        self.assertIn("MoM revenue change", content)
        self.assertIn("last two months profit/loss", content)
        self.assertIn("Profit Margin Baseline", content)
        self.assertIn("Net Income", content)

    def test_references(self):
        result = RAGResult(
            "What is revenue?",
            "Revenue answer.",
            [FakeDocument("Revenue comes from sales rows.", "sales_log.json")],
            "Prompt",
        )

        references = result.references()

        self.assertEqual(references[0]["reference"], 1)
        self.assertEqual(references[0]["source"], "sales_log.json")
        self.assertEqual(
            references[0]["snippet"],
            "Revenue comes from sales rows.",
        )


if __name__ == "__main__":
    unittest.main()
