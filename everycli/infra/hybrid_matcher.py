"""
Hybrid Matcher: Combines TF-IDF for exact keywords and SemanticMatcher for meaning.
"""

from everycli.core.interfaces import Matcher as MatcherProtocol
from everycli.core.models import Scenario
from everycli.infra.tfidf_matcher import TFIDFMatcher
from everycli.infra.semantic_matcher import SemanticMatcher

class HybridMatcher:
    def __init__(self, semantic_weight: float = 0.6, fast_threshold: float = 0.45):
        self.semantic_weight = semantic_weight
        self.fast_threshold = fast_threshold
        self.tfidf = TFIDFMatcher()
        self.semantic = None
        self._scenarios = []

    def fit(self, scenarios: list[Scenario]) -> None:
        self.tfidf.fit(scenarios)
        self._scenarios = scenarios

    def match(self, query: str, top_k: int = 3) -> list[tuple[Scenario, float]]:
        # Fast path : TF-IDF en 0.05 seconde
        tfidf_results = self.tfidf.match(query, top_k=20)
        
        # Si TF-IDF est très confiant, on retourne le résultat immédiatement
        if tfidf_results and tfidf_results[0][1] >= self.fast_threshold:
            from rich.console import Console
            Console().print("  [dim]>> Reponse instantanee (Mots-cles directs)[/dim]")
            return tfidf_results[:top_k]

        from rich.console import Console
        Console().print("  [dim][IA] Analyse semantique en cours (peut prendre 10s)...[/dim]")
        
        if self.semantic is None:
            self.semantic = SemanticMatcher()
            self.semantic.fit(self._scenarios)

        semantic_results = {s.id: score for s, score in self.semantic.match(query, top_k=20)}
        
        tfidf_dict = {s.id: score for s, score in tfidf_results}
        
        combined = []
        for scenario in self._scenarios:
            tfidf_score = tfidf_dict.get(scenario.id, 0.0)
            sem_score = semantic_results.get(scenario.id, 0.0)
            
            # Weighted average
            final_score = (tfidf_score * (1 - self.semantic_weight)) + (sem_score * self.semantic_weight)
            
            if final_score > 0.05:
                combined.append((scenario, final_score))
                
        # Sort and return
        combined.sort(key=lambda x: x[1], reverse=True)
        
        # Round the scores for display
        return [(s, round(score, 4)) for s, score in combined[:top_k]]

assert isinstance(HybridMatcher(), MatcherProtocol), "HybridMatcher must implement MatcherProtocol"
