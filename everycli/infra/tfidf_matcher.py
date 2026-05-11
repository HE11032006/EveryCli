"""
BM25 based matcher implementation.
Finds the most relevant scenarios for a given query using lexical matching.
"""

import unicodedata
import re
import numpy as np
from rank_bm25 import BM25Okapi

from everycli.core.models import Scenario
from everycli.core.interfaces import Matcher as MatcherProtocol


def _normalize(text: str) -> str:
    """
    Lowercase, remove accents, strip punctuation.
    Kept for backward compatibility with existing tests.
    """
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # Remplace TOUTE la ponctuation par des espaces
    text = re.sub(r"[^\w\s]+", " ", text)
    # Écrase les espaces multiples en un seul
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _tokenize(text: str) -> list[str]:
    """
    Tokenize text for BM25. 
    More permissive than _normalize to keep command-specific chars like - and /.
    """
    text = text.lower()
    text = unicodedata.normalize("NFD", text)
    text = "".join(c for c in text if unicodedata.category(c) != "Mn")
    # On garde les lettres, chiffres et les caractères de commande / et -
    return re.findall(r"[\w/-]+", text)


def _scenario_to_document(scenario: Scenario) -> str:
    """
    Converts a scenario into a searchable text document.
    Boosting is applied here by repeating fields.
    """
    # Boost demandé : Tags x2.5 (on arrondit à 3), Commande x3.0
    tags_part = " ".join(scenario.tags * 3)
    cmd_part = " ".join([scenario.command.linux] * 3)
    return f"{scenario.description} {tags_part} {scenario.explanation} {cmd_part}"


class TFIDFMatcher:
    """
    Matches user queries to scenarios using BM25.
    (Kept the name TFIDFMatcher to avoid breaking imports in HybridMatcher).
    """

    def __init__(self):
        self._bm25 = None
        self._scenarios: list[Scenario] = []
        self._fitted = False

    def fit(self, scenarios: list[Scenario]) -> None:
        if not scenarios:
            return

        self._scenarios = scenarios
        corpus = [_tokenize(_scenario_to_document(s)) for s in scenarios]
        self._bm25 = BM25Okapi(corpus)
        self._fitted = True

    def match(self, query: str, top_k: int = 3) -> list[tuple[Scenario, float]]:
        if not self._fitted or not self._scenarios:
            return []

        tokenized_query = _tokenize(query)
        if not tokenized_query:
            return []

        # BM25 scores are not naturally between 0 and 1. 
        # We perform a simple Min-Max normalization to approximate a confidence score.
        raw_scores = self._bm25.get_scores(tokenized_query)
        
        max_score = np.max(raw_scores) if len(raw_scores) > 0 else 0
        if max_score > 0:
            scores = raw_scores / max_score
        else:
            scores = raw_scores

        top_indices = np.argsort(scores)[::-1][:top_k]

        return [
            (self._scenarios[i], round(float(scores[i]), 4))
            for i in top_indices
            if scores[i] > 0.0
        ]


assert isinstance(TFIDFMatcher(), MatcherProtocol), \
    "TFIDFMatcher must implement MatcherProtocol"