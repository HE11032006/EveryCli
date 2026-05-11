"""
SearchEngine — orchestrates the full search flow.
Depends only on interfaces, never on concrete implementations.
This is the heart of EveryCLI.
"""

from everycli.core.interfaces import Matcher, OSResolver, ScenarioLoader
from everycli.core.models import SearchResult


class SearchEngine:
    """
    Orchestrates: load scenarios → fit matcher → resolve query → return results.
    Receives all dependencies via injection — fully testable without real files or OS.
    """

    def __init__(
        self,
        loader: ScenarioLoader,
        matcher: Matcher,
        os_resolver: OSResolver,
    ):
        self._loader = loader
        self._matcher = matcher
        self._os_resolver = os_resolver
        self._ready = False

    def boot(self) -> None:
        """Load scenarios and fit the matcher. Call once at startup."""
        self._scenarios = self._loader.load_all()
        self._matcher.fit(self._scenarios)
        self._ready = True

    def _parse_query(self, query: str) -> tuple[list[str], str]:
        """
        Parses scopes from the query (e.g. 'git, docker: search term').
        Returns ([scopes], clean_query).
        """
        if ":" not in query:
            return [], query

        parts = query.split(":", 1)
        scope_part = parts[0].strip()
        clean_query = parts[1].strip()

        # On extrait les tags (séparés par virgules)
        scopes = [s.strip().lower() for s in scope_part.split(",")]
        return scopes, clean_query

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]:
        """
        Search for the most relevant scenarios matching the query.
        Supports scoped search via 'tag: query'.
        """
        if not self._ready:
            raise RuntimeError("SearchEngine.boot() must be called before search().")

        scopes, clean_query = self._parse_query(query)
        
        # Filtrage par scope si nécessaire
        if scopes:
            filtered_scenarios = [
                s for s in self._scenarios 
                if any(tag in s.tags for tag in scopes)
            ]
            # On ne fait rien si aucun scénario ne correspond au scope
            if filtered_scenarios:
                # On temporairement fit le matcher sur le subset (ou on filtre après)
                # Pour garder la perf, on va laisser le matcher faire son travail 
                # et filtrer les résultats ensuite, MAIS en demandant plus de candidats.
                matches = self._matcher.match(clean_query, top_k=top_k * 5)
                matches = [
                    (s, score) for s, score in matches 
                    if any(tag in s.tags for tag in scopes)
                ]
            else:
                # Si le scope n'existe pas, on ignore le scope et on cherche normalement
                matches = self._matcher.match(query, top_k=top_k)
        else:
            matches = self._matcher.match(query, top_k=top_k)

        current_os = self._os_resolver.resolve()
        
        return [
            SearchResult(
                scenario=scenario,
                resolved_command=scenario.command.for_os(current_os),
                score=score,
            )
            for scenario, score in matches[:top_k]
        ]