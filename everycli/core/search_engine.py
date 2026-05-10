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
        scenarios = self._loader.load_all()
        self._matcher.fit(scenarios)
        self._ready = True

    def search(self, query: str, top_k: int = 3) -> list[SearchResult]:
        """
        Search for the most relevant scenarios matching the query.
        Returns a ranked list of SearchResult, best match first.
        """
        if not self._ready:
            raise RuntimeError("SearchEngine.boot() must be called before search().")

        current_os = self._os_resolver.resolve()
        matches = self._matcher.match(query, top_k=top_k)

        return [
            SearchResult(
                scenario=scenario,
                resolved_command=scenario.command.for_os(current_os),
                score=score,
            )
            for scenario, score in matches
        ]