"""
Semantic matcher using sentence-transformers.
With embedding cache — encodes once, loads instantly after.
"""

import os
import hashlib
import json
import logging
import warnings
import numpy as np
from pathlib import Path

# Masquer totalement les warnings de HuggingFace et les barres de progression
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["TRANSFORMERS_VERBOSITY"] = "error"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"

warnings.filterwarnings("ignore")
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)

from everycli.core.models import Scenario
from everycli.core.interfaces import Matcher as MatcherProtocol

MODEL_NAME = "all-MiniLM-L2-v2"
CACHE_DIR = Path.home() / ".everycli" / "cache"


def _scenario_to_document(scenario: Scenario) -> str:
    tags_boosted = " ".join(scenario.tags * 2)
    return f"{scenario.description} {tags_boosted} {scenario.explanation}"


def _compute_cache_key(documents: list[str]) -> str:
    content = json.dumps(documents, ensure_ascii=False, sort_keys=True)
    return hashlib.md5(content.encode()).hexdigest()


class SemanticMatcher:

    def __init__(self, model_name: str = MODEL_NAME, cache_dir: Path = CACHE_DIR):
        self._model_name = model_name
        self._cache_dir = cache_dir
        self._model = None
        self._scenarios: list[Scenario] = []
        self._embeddings = None
        self._fitted = False

    def _load_model(self) -> None:
        if self._model is None:
            # Import paresseux (lazy) pour ne pas ralentir le démarrage du CLI
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)

    def _cache_path(self, key: str) -> Path:
        return self._cache_dir / f"{key}.npy"

    def _load_cache(self, key: str):
        path = self._cache_path(key)
        if path.exists():
            try:
                return np.load(str(path))
            except Exception:
                # Cache corrompu — on le supprime
                path.unlink(missing_ok=True)
        return None

    def _save_cache(self, key: str, embeddings) -> None:
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            np.save(str(self._cache_path(key)), embeddings)
        except Exception as e:
            # Cache non critique — on continue sans
            print(f"[cache] Impossible de sauvegarder : {e}")

    def fit(self, scenarios: list[Scenario]) -> None:
        if not scenarios:
            return

        self._scenarios = scenarios
        documents = [_scenario_to_document(s) for s in scenarios]
        cache_key = _compute_cache_key(documents)

        cached = self._load_cache(cache_key)
        if cached is not None:
            self._embeddings = cached
            self._fitted = True
            return  # Cache hit -> On esquive le _load_model() qui coûte 3s

        # Cache miss — on charge le modèle, on encode et on sauvegarde
        self._load_model()
        self._embeddings = self._model.encode(
            documents,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        self._save_cache(cache_key, self._embeddings)
        self._fitted = True

    def _query_cache_path(self, query: str) -> Path:
        key = hashlib.md5(query.encode()).hexdigest()
        return self._cache_dir / f"query_{key}.npy"

    def _load_query_cache(self, query: str):
        path = self._query_cache_path(query)
        if path.exists():
            try:
                return np.load(str(path))
            except Exception:
                path.unlink(missing_ok=True)
        return None

    def _save_query_cache(self, query: str, embedding) -> None:
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            np.save(str(self._query_cache_path(query)), embedding)
        except Exception:
            pass

    def match(self, query: str, top_k: int = 3) -> list[tuple[Scenario, float]]:
        if not self._fitted or not self._scenarios:
            return []

        from sklearn.metrics.pairwise import cosine_similarity

        # Essaie le cache de query d'abord — évite de charger le modèle
        query_embedding = self._load_query_cache(query)
        if query_embedding is None:
            self._load_model()
            query_embedding = self._model.encode(
                [query],
                convert_to_numpy=True,
                show_progress_bar=False,
            )
            self._save_query_cache(query, query_embedding)

        scores = cosine_similarity(query_embedding, self._embeddings).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        return [
            (self._scenarios[i], round(float(scores[i]), 4))
            for i in top_indices
            if scores[i] > 0.0
        ]


assert isinstance(SemanticMatcher(), MatcherProtocol), \
    "SemanticMatcher must implement MatcherProtocol"