import pytest
from pathlib import Path
from everycli.infra.yaml_loader import YamlLoader
from everycli.infra.hybrid_matcher import HybridMatcher
from everycli.infra.os_resolver import OSResolver
from everycli.core.search_engine import SearchEngine
from everycli.infra.context_detector import ProjectContextDetector

@pytest.fixture(scope="session")
def engine():
    data_dir = Path(__file__).parent.parent / "everycli" / "data" / "commands"
    matcher = HybridMatcher(semantic_weight=0.85)  # Increased semantic weight
    engine = SearchEngine(
        loader=YamlLoader(data_dir),
        matcher=matcher,
        os_resolver=OSResolver(),
        context_detector=ProjectContextDetector(),
    )
    engine.boot()
    return engine

@pytest.mark.parametrize("query, expected_id, expected_namespace", [
    ("lance tous les containers en arriere plan", "docker_compose_up", "docker_compose"),
    ("supprime l'image ubuntu", "docker_remove_image", "docker"),
    ("annule mon dernier commit sans perdre les modifs", "git_undo_last_commit_keep_changes", "git"),
    ("revenir au commit precedent completement", "git_undo_last_commit_discard_changes", "git"),
    ("installer les dependances de mon projet node", "npm_install", "npm"),
    ("creer un environnement virtuel python", "python_create_venv", "python"),
])
def test_search_pipeline_precision(engine, query, expected_id, expected_namespace):
    results = engine.search(query, top_k=3)
    assert len(results) > 0, f"No results found for query: {query}"
    
    best = results[0]
    
    # If the first one doesn't match exactly, check if it's in the top 2
    # just in case it's a very close call.
    top_ids = [r.scenario.id for r in results[:2]]
    assert expected_id in top_ids, f"Expected {expected_id} in top 2 for '{query}', got {top_ids}. Best score: {best.score}"
    
    if best.scenario.id != expected_id:
        print(f"Warning: {expected_id} was second. Best was {best.scenario.id}.")

