"""
Semantic matcher using sentence-transformers.
Replaces TFIDFMatcher — same interface, smarter matching.
Understands meaning, not just keywords.
"""

import os
import logging
import warnings
import numpy as np

# Masquer les warnings de HuggingFace et les barres de progression
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)

from everycli.core.models import Scenario
from everycli.core.interfaces import Matcher as MatcherProtocol

MODEL_NAME = "all-MiniLM-L6-v2"


def _scenario_to_document(scenario: Scenario) -> str:
    """
    Converts a scenario into a single searchable document.
    Tags repeated to boost their semantic weight.
    """
    tags_boosted = " ".join(scenario.tags * 2)
    return f"{scenario.description} {tags_boosted} {scenario.explanation}"


class SemanticMatcher:
    """
    Matches user queries to scenarios using semantic embeddings.
    Downloads the model once (~80MB), then works fully offline.
    Must call fit() before match().
    """

    def __init__(self, model_name: str = MODEL_NAME):
        self._model_name = model_name
        self._model = None
        self._scenarios: list[Scenario] = []
        self._embeddings = None
        self._fitted = False

    def _load_model(self) -> None:
        """Lazy load — model is loaded only when first needed."""
        if self._model is None:
            # Lazy import to avoid 7 seconds penalty on CLI boot
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)

    def fit(self, scenarios: list[Scenario]) -> None:
        if not scenarios:
            return

        self._load_model()
        self._scenarios = scenarios
        documents = [_scenario_to_document(s) for s in scenarios]
        self._embeddings = self._model.encode(
            documents,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        self._fitted = True

    def match(self, query: str, top_k: int = 3) -> list[tuple[Scenario, float]]:
        if not self._fitted or not self._scenarios:
            return []

        from sklearn.metrics.pairwise import cosine_similarity
        
        self._load_model()
        query_embedding = self._model.encode(
            [query],
            convert_to_numpy=True,
            show_progress_bar=False,
        )

        scores = cosine_similarity(query_embedding, self._embeddings).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        return [
            (self._scenarios[i], round(float(scores[i]), 4))
            for i in top_indices
            if scores[i] > 0.0
        ]


assert isinstance(SemanticMatcher(), MatcherProtocol), \
    "SemanticMatcher must implement MatcherProtocol"