"""
TF-IDF based matcher implementation.
Finds the most relevant scenarios for a given query.
Phase 2: this gets swapped for SemanticMatcher — SearchEngine never changes.
"""

import unicodedata
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

from everycli.core.models import Scenario
from everycli.core.interfaces import Matcher as MatcherProtocol


def _normalize(text: str) -> str:
    """Lowercase, remove accents, strip punctuation."""
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    text = re.sub(r"[^\w\s]+", " ", text)
    return text.strip()


def _scenario_to_document(scenario: Scenario) -> str:
    """
    Converts a scenario into a single searchable text document.
    Tags get repeated to boost their weight in TF-IDF scoring.
    """
    tags_boosted = " ".join(scenario.tags * 3)
    return f"{scenario.description} {tags_boosted} {scenario.explanation}"


class TFIDFMatcher:
    """
    Matches user queries to scenarios using TF-IDF + cosine similarity.
    Must call fit() before match().
    """

    def __init__(self):
        self._vectorizer = TfidfVectorizer(analyzer="word")
        self._scenarios: list[Scenario] = []
        self._matrix = None
        self._fitted = False

    def fit(self, scenarios: list[Scenario]) -> None:
        if not scenarios:
            return

        self._scenarios = scenarios
        documents = [_normalize(_scenario_to_document(s)) for s in scenarios]
        self._matrix = self._vectorizer.fit_transform(documents)
        self._fitted = True

    def match(self, query: str, top_k: int = 3) -> list[tuple[Scenario, float]]:
        if not self._fitted or not self._scenarios:
            return []

        normalized_query = _normalize(query)
        query_vector = self._vectorizer.transform([normalized_query])
        scores = cosine_similarity(query_vector, self._matrix).flatten()

        top_indices = np.argsort(scores)[::-1][:top_k]

        return [
            (self._scenarios[i], round(float(scores[i]), 4))
            for i in top_indices
            if scores[i] > 0.0
        ]


assert isinstance(TFIDFMatcher(), MatcherProtocol), \
    "TFIDFMatcher must implement MatcherProtocol"