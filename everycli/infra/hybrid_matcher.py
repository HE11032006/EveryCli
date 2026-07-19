from everycli.core.interfaces import Matcher as MatcherProtocol
from everycli.core.models import Scenario
from everycli.infra.tfidf_matcher import TFIDFMatcher
from everycli.infra.semantic_matcher import SemanticMatcher


class HybridMatcher:
    """
    Two-stage matcher:
    1. TF-IDF — instant, keyword-based
    2. Semantic — slower, meaning-based, always pre-loaded
    
    The semantic model is fitted once at boot() and cached on disk.
    match() never triggers a fit — always fast after boot.
    """

    def __init__(
        self,
        semantic_weight: float = 0.6,
        fast_threshold: float = 0.55,
        ambiguity_margin: float = 0.12,
    ):
        self._semantic_weight = semantic_weight
        self._fast_threshold = fast_threshold
        self._ambiguity_margin = ambiguity_margin
        self._tfidf = TFIDFMatcher()
        self._semantic = SemanticMatcher()
        self._scenarios: list[Scenario] = []
        self._fitted = False
        # Signal for the caller to display a loading message
        self.used_semantic: bool = False

    def _can_use_fast_path(self, results: list[tuple[Scenario, float]]) -> bool:
        """Use lexical-only only when it is both strong *and* unambiguous.

        A high BM25 score is not sufficient: terms shared by two commands can
        rank the wrong command first with high confidence.  A small gap between
        the first two candidates is therefore sent to the semantic reranker.
        """
        if not results or results[0][1] < self._fast_threshold:
            return False
        if len(results) == 1:
            return True
        return results[0][1] - results[1][1] >= self._ambiguity_margin

    def fit(self, scenarios: list[Scenario]) -> None:
        """
        Fit both matchers at boot.
        Semantic uses disk cache — only slow on first ever run.
        """
        if not scenarios:
            return

        self._scenarios = scenarios
        self._tfidf.fit(scenarios)
        self._semantic.fit(scenarios)   # ← uses cache, fast after first run
        self._fitted = True

    def match(self, query: str, top_k: int = 3) -> list[tuple[Scenario, float]]:
        if not self._fitted:
            return []

        self.used_semantic = False

        # ── Fast path — TF-IDF only ───────────────────────────────────────────
        tfidf_results = self._tfidf.match(query, top_k=20)

        if self._can_use_fast_path(tfidf_results):
            return tfidf_results[:top_k]

        # ── Slow path — combine TF-IDF + Semantic ────────────────────────────
        self.used_semantic = True

        semantic_results = self._semantic.match(query, top_k=20)

        tfidf_dict = {s.id: score for s, score in tfidf_results}
        semantic_dict = {s.id: score for s, score in semantic_results}

        combined = []
        for scenario in self._scenarios:
            tfidf_score = tfidf_dict.get(scenario.id, 0.0)
            sem_score = semantic_dict.get(scenario.id, 0.0)

            final_score = (
                tfidf_score * (1 - self._semantic_weight)
                + sem_score * self._semantic_weight
            )

            if final_score >= 0.40:
                combined.append((scenario, round(final_score, 4)))

        combined.sort(key=lambda x: x[1], reverse=True)
        return combined[:top_k]


assert isinstance(HybridMatcher(), MatcherProtocol), \
    "HybridMatcher must implement MatcherProtocol"
