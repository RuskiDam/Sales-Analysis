import importlib
import json

from sales_analysis.ai.ai_guardrails import GuardrailComponentFactory
from sales_analysis.project_paths import ProjectPaths


class RAGDependencyLoader:
    """Loads Haystack lazily so unit tests can use lightweight fakes."""

    dependency_paths = {
        "Document": ("haystack", "Document"),
        "Pipeline": ("haystack", "Pipeline"),
        "DocumentCleaner": (
            "haystack.components.preprocessors",
            "DocumentCleaner",
        ),
        "DocumentSplitter": (
            "haystack.components.preprocessors",
            "DocumentSplitter",
        ),
        "InMemoryEmbeddingRetriever": (
            "haystack.components.retrievers.in_memory",
            "InMemoryEmbeddingRetriever",
        ),
        "InMemoryDocumentStore": (
            "haystack.document_stores.in_memory",
            "InMemoryDocumentStore",
        ),
        "SentenceTransformersDocumentEmbedder": (
            "haystack.components.embedders",
            "SentenceTransformersDocumentEmbedder",
        ),
        "SentenceTransformersTextEmbedder": (
            "haystack.components.embedders",
            "SentenceTransformersTextEmbedder",
        ),
    }

    @staticmethod
    def load():
        modules = RAGDependencyLoader.import_haystack()
        return RAGDependencyLoader.dependency_map(modules)

    @staticmethod
    def import_haystack():
        """Import optional Haystack classes only when real RAG is constructed."""

        try:
            return {
                name: RAGDependencyLoader.load_class(module, class_name)
                for name, (module, class_name) in (
                    RAGDependencyLoader.dependency_paths.items()
                )
            }
        except ImportError as error:
            raise ValueError(
                "Haystack RAG dependencies are missing. "
                "Install requirements.txt first."
            ) from error

    @staticmethod
    def load_class(module_name, class_name):
        module = importlib.import_module(module_name)
        return getattr(module, class_name)

    @staticmethod
    def dependency_map(modules):
        """Expose imported classes behind stable keys used by tests and pipeline."""

        return {
            "Document": modules["Document"],
            "DocumentCleaner": modules["DocumentCleaner"],
            "DocumentSplitter": modules["DocumentSplitter"],
            "InMemoryDocumentStore": modules["InMemoryDocumentStore"],
            "InMemoryEmbeddingRetriever": (
                modules["InMemoryEmbeddingRetriever"]
            ),
            "Pipeline": modules["Pipeline"],
            "SentenceTransformersDocumentEmbedder": (
                modules["SentenceTransformersDocumentEmbedder"]
            ),
            "SentenceTransformersTextEmbedder": (
                modules["SentenceTransformersTextEmbedder"]
            ),
        }


class RAGCorpus:
    """Predefined project corpus used by the A.I. tab.

    Users cannot upload arbitrary files. Maintainers add corpus files by placing
    supported files in `docs/`.
    """

    corpus_path = "docs"
    source_extensions = {".json", ".md", ".txt"}

    def documents(self):
        """Load source files into Haystack-ready document dictionaries."""

        documents = []
        for source in self.sources():
            source_path = source["source"]
            path = ProjectPaths.resolve(source_path)
            text = self.source_text(path)
            if text:
                documents.append(
                    {
                        "content": text,
                        "meta": {
                            "source": source_path,
                            "title": self.title(source_path),
                        },
                    }
                )

        return documents

    def sources(self):
        """Return existing corpus files with display metadata for the UI."""

        sources = []
        for path in self.source_files():
            source_path = self.source_name(path)
            sources.append(
                {
                    "source": source_path,
                    "title": self.title(source_path),
                    "size_kb": round(path.stat().st_size / 1024, 1),
                }
            )

        return sources

    def source_files(self):
        corpus_dir = ProjectPaths.resolve(self.corpus_path)
        if not corpus_dir.exists():
            return []

        return [
            path
            for path in sorted(corpus_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in self.source_extensions
        ]

    @staticmethod
    def source_name(path):
        try:
            return path.relative_to(ProjectPaths.project_root).as_posix()
        except ValueError:
            return path.name

    @staticmethod
    def source_text(path):
        raw_text = path.read_text(encoding="utf-8")
        if path.suffix == ".json":
            data = json.loads(raw_text)
            return json.dumps(data, indent=2)

        return raw_text

    @staticmethod
    def title(source_path):
        return source_path.replace("/", " / ")


class RAGResult:
    def __init__(self, question, answer, documents, prompt):
        self.question = question
        self.answer = answer
        self.documents = documents
        self.prompt = prompt

    def references(self):
        """Return referenced document names without exposing retrieved text."""

        rows = []
        seen_sources = set()
        for document in self.documents:
            source = document.meta.get("source", "Unknown")
            if source in seen_sources:
                continue

            seen_sources.add(source)
            rows.append({"Document": source})

        return rows


class HaystackRAGPipeline:
    embedding_model = "sentence-transformers/all-MiniLM-L6-v2"
    split_length = 150
    split_overlap = 50
    top_k = 4

    def __init__(
        self,
        corpus=None,
        dependencies=None,
        guardrail_component=None,
    ):
        self.corpus = corpus or RAGCorpus()
        self.dependencies = dependencies or RAGDependencyLoader.load()
        self.guardrail_component = (
            guardrail_component
            or GuardrailComponentFactory.create()
        )
        self.document_store = self.dependencies["InMemoryDocumentStore"]()
        self.indexed_documents = []
        self.retrieval_pipeline = None

    def index(self):
        """Clean, split, embed, and cache the fixed corpus in memory."""

        if self.indexed_documents:
            return self.indexed_documents

        raw_documents = self.haystack_documents()
        if not raw_documents:
            raise ValueError("No RAG documents are available to index.")

        cleaned_documents = self.clean_documents(raw_documents)
        split_documents = self.split_documents(cleaned_documents)
        embedded_documents = self.embed_documents(split_documents)
        self.document_store.write_documents(embedded_documents)
        self.indexed_documents = embedded_documents
        return self.indexed_documents

    def haystack_documents(self):
        document_class = self.dependencies["Document"]
        return [
            document_class(content=row["content"], meta=row["meta"])
            for row in self.corpus.documents()
        ]

    def clean_documents(self, documents):
        cleaner = self.dependencies["DocumentCleaner"]()
        result = cleaner.run(documents=documents)
        return result["documents"]

    def split_documents(self, documents):
        splitter_class = self.dependencies["DocumentSplitter"]
        splitter = splitter_class(
            split_by="word",
            split_length=self.split_length,
            split_overlap=self.split_overlap,
        )
        result = splitter.run(documents=documents)
        return result["documents"]

    def embed_documents(self, documents):
        embedder_class = self.dependencies[
            "SentenceTransformersDocumentEmbedder"
        ]
        embedder = embedder_class(model=self.embedding_model)
        result = embedder.run(documents)
        return result["documents"]

    def retrieve(self, question):
        self.index()
        pipeline = self.query_pipeline()
        try:
            result = pipeline.run(
                {
                    "guardrails": {"prompt": question},
                    "retriever": {"top_k": self.top_k},
                }
            )
        except Exception as error:
            raise ValueError(
                "RAG retrieval failed while processing the question."
            ) from error

        return result["retriever"]["documents"]

    def query_pipeline(self):
        """Build the Haystack retrieval graph once and reuse it for questions."""

        if self.retrieval_pipeline:
            return self.retrieval_pipeline

        pipeline = self.dependencies["Pipeline"]()
        text_embedder = self.dependencies["SentenceTransformersTextEmbedder"](
            model=self.embedding_model
        )
        retriever = self.dependencies["InMemoryEmbeddingRetriever"](
            document_store=self.document_store
        )
        pipeline.add_component("guardrails", self.guardrail_component)
        pipeline.add_component("text_embedder", text_embedder)
        pipeline.add_component("retriever", retriever)
        pipeline.connect("guardrails.prompt", "text_embedder.text")
        pipeline.connect(
            "text_embedder.embedding",
            "retriever.query_embedding",
        )
        self.retrieval_pipeline = pipeline
        return self.retrieval_pipeline

    def answer(self, question, llm_client, instruction_context=""):
        documents = self.retrieve(question)
        prompt = self.prompt(question, documents, instruction_context)
        answer = llm_client.ask(prompt)
        return RAGResult(question, answer, documents, prompt)

    @staticmethod
    def prompt(question, documents, instruction_context=""):
        """Assemble retrieved chunks and app instructions into one LLM prompt."""

        context_lines = []
        for index, document in enumerate(documents, start=1):
            source = document.meta.get("source", "Unknown")
            context_lines.append(
                f"[{index}] Source: {source}\n{document.content}"
            )

        context = "\n\n".join(context_lines)
        return (
            "Answer using only the retrieved project context. "
            "Keep the answer under 80 words and use no more than 3 bullets. "
            "Do not add a preamble. "
            "If the context does not contain the answer, say "
            "\"I don't know from current documents.\" Cite references like "
            "[1] when using a retrieved chunk.\n\n"
            f"Instructions:\n{instruction_context}\n\n"
            f"Context:\n{context}\n\n"
            f"Question: {question}\n"
            "Answer:"
        )
