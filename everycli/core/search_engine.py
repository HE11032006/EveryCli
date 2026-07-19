"""
SearchEngine — orchestrates the full search flow.
Depends only on interfaces, never on concrete implementations.
This is the heart of EveryCLI.
"""

import re

from everycli.core.interfaces import ContextDetector, Matcher, OSResolver, ScenarioLoader
from everycli.core.models import SearchResult

_NAMESPACE_ALIASES: dict[str, tuple[str, ...]] = {
    "bash_command": ("bash", "shell script"),
    "composer": ("composer", "php"),
    "docker": ("docker",),
    "docker_compose": ("docker compose", "compose"),
    "git": ("git",),
    "linux": ("linux", "systemd", "systemctl"),
    "npm": ("npm", "node", "nodejs"),
    "python": ("python", "pip", "pytest", "venv", "virtualenv"),
    "ssh": ("ssh", "scp", "sftp"),
}

_CONTEXT_COMPETITIVE_RATIO = 0.85


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
        context_detector: ContextDetector | None = None,
    ):
        self._loader = loader
        self._matcher = matcher
        self._os_resolver = os_resolver
        self._context_detector = context_detector
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

    @staticmethod
    def _matches_scope(scenario, scopes: list[str]) -> bool:
        """A scenario matches a scope if its namespace matches directly (reliable,
        always present) or, failing that, if one of its tags matches (fallback, for
        entries whose namespace doesn't line up 1:1 with how a user might scope)."""
        if scenario.namespace:
            return scenario.namespace.lower() in scopes
        return any(tag.lower() in scopes for tag in scenario.tags)

    def _query_namespace_scopes(self, query: str) -> list[str]:
        """Recognize an ecosystem explicitly named in natural language."""
        normalized_query = re.sub(r"[_-]+", " ", query.lower())
        namespaces = {scenario.namespace.lower() for scenario in self._scenarios if scenario.namespace}
        candidates: list[tuple[str, str]] = []
        for namespace in namespaces:
            candidates.append((re.sub(r"[_-]+", " ", namespace), namespace))
            candidates.extend((alias, namespace) for alias in _NAMESPACE_ALIASES.get(namespace, ()))
        for phrase, namespace in sorted(candidates, key=lambda item: len(item[0]), reverse=True):
            if re.search(rf"(?<!\w){re.escape(phrase)}(?!\w)", normalized_query):
                return [namespace]
        return []

    @staticmethod
    def _context_is_competitive(matches: list[tuple], context_matches: list[tuple]) -> bool:
        """Keep context only when it is close to the best global candidate."""
        if not matches or not context_matches:
            return False
        best_score = matches[0][1]
        return best_score > 0 and context_matches[0][1] >= best_score * _CONTEXT_COMPETITIVE_RATIO

    def search(
        self,
        query: str,
        top_k: int = 3,
        context_override: list[str] | None = None,
    ) -> list[SearchResult]:
        """
        Search for the most relevant scenarios matching the query.
        Supports scoped search via 'tag: query', and auto-scoping from either:
          - `context_override`: namespaces detected by the caller (e.g. the
            daemon, forwarding what its client detected in the user's real
            cwd — the daemon's own cwd isn't meaningful for this), or
          - the injected ContextDetector, when no override is given (used for
            in-process/local search, where self's cwd IS the user's cwd).
        `context_override` takes priority over the injected ContextDetector.
        An explicit empty list means "checked, nothing detected" and is
        treated the same as no context, not as "no override given".
        """
        if not self._ready:
            raise RuntimeError("SearchEngine.boot() must be called before search().")

        scopes, clean_query = self._parse_query(query)
        implicit_scope = False

        if not scopes:
            scopes = self._query_namespace_scopes(query)
            if scopes:
                clean_query = query
            else:
                if context_override is not None:
                    detected = context_override
                elif self._context_detector is not None:
                    detected = self._context_detector.detect()
                else:
                    detected = []
                if detected:
                    scopes = [d.strip().lower() for d in detected]
                    clean_query = query
                    implicit_scope = True

        # Filtrage par scope si nécessaire (explicite ou déduit du contexte)
        if scopes:
            filtered_scenarios = [
                s for s in self._scenarios
                if self._matches_scope(s, scopes)
            ]
            # On ne fait rien si aucun scénario ne correspond au scope
            if filtered_scenarios:
                # On temporairement fit le matcher sur le subset (ou on filtre après)
                # Pour garder la perf, on va laisser le matcher faire son travail 
                # et filtrer les résultats ensuite, MAIS en demandant plus de candidats.
                matches = self._matcher.match(clean_query, top_k=top_k * 5)
                scoped_matches = [
                    (s, score) for s, score in matches
                    if self._matches_scope(s, scopes)
                ]
                if implicit_scope:
                    matches = scoped_matches if self._context_is_competitive(matches, scoped_matches) else matches
                else:
                    matches = scoped_matches
            elif implicit_scope:
                # Contexte détecté mais aucun scénario ne correspond : on ignore
                # silencieusement le contexte plutôt que de renvoyer une liste vide.
                matches = self._matcher.match(query, top_k=top_k)
            else:
                # Si le scope explicite n'existe pas, on ignore le scope et on cherche normalement
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