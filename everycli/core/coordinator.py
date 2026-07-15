"""
SearchCoordinator — orchestre la recherche entre le mode Daemon et le mode Local.
"""

from typing import List, Optional
from rich.console import Console

from everycli.core.models import SearchResult
from everycli.infra import daemon_client
from everycli.infra.daemon_client import DaemonResult, DaemonError

class SearchCoordinator:
    def __init__(self, console: Console, data_dir: str):
        self.console = console
        self.data_dir = data_dir

    def execute_search(
        self, 
        query: str, 
        top_k: int = 1, 
        no_daemon: bool = False
    ) -> List[SearchResult]:
        """
        Tente une recherche via le daemon, bascule en local si besoin.
        """
        if not no_daemon:
            resp = daemon_client.search(query, top_k=top_k)
            if isinstance(resp, DaemonResult):
                return self._map_daemon_results(resp.results)
            
            self.console.print("  [yellow]⚠ Daemon indisponible — basculement en mode direct.[/yellow]")
        
        return self._execute_local_search(query, top_k)

    def _execute_local_search(self, query: str, top_k: int) -> List[SearchResult]:
        from everycli.infra.hybrid_matcher import HybridMatcher
        from everycli.core.search_engine import SearchEngine
        from everycli.infra.yaml_loader import YamlLoader
        from everycli.infra.os_resolver import OSResolver
        from everycli.infra.context_detector import ProjectContextDetector
        from pathlib import Path

        matcher = HybridMatcher(semantic_weight=0.6)
        engine = SearchEngine(
            loader=YamlLoader(Path(self.data_dir)),
            matcher=matcher,
            os_resolver=OSResolver(),
            # Ici on tourne dans le même process que l'utilisateur, donc le
            # cwd est bien le sien — contrairement au daemon (voir daemon.py).
            context_detector=ProjectContextDetector(),
        )
        
        with self.console.status("[dim]Chargement local...[/dim]", spinner="dots"):
            engine.boot()
            return engine.search(query, top_k=top_k)

    def _map_daemon_results(self, raw: list[dict]) -> List[SearchResult]:
        from everycli.core.models import Scenario, Command, SearchResult
        
        results = []
        for r in raw:
            cmd = Command(linux=r["command"], windows=r["command"], macos=r["command"])
            scenario = Scenario(
                id=r["id"],
                description=r["description"],
                tags=r.get("tags", []),
                command=cmd,
                explanation=r.get("explanation", ""),
                warning=r.get("warning", ""),
                namespace=r.get("namespace", ""),
            )
            results.append(SearchResult(
                scenario=scenario,
                resolved_command=r["command"],
                score=r.get("score", 0.0),
            ))
        return results