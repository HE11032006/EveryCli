"""
Semantic matcher using sentence-transformers.
With embedding cache — encodes once, loads instantly after.
"""

import os
import sys
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

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
CACHE_DIR = Path.home() / ".everycli" / "cache"


def _scenario_to_document(scenario: Scenario) -> str:
    # Boost demandé : Tags x2.5 (on arrondit à 3), Commande x3.0
    tags_boosted = " ".join(scenario.tags * 3)
    cmd_boosted = " ".join([scenario.command.linux] * 3)
    return f"{scenario.description} {tags_boosted} {scenario.explanation} {cmd_boosted}"


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
            try:
                from sentence_transformers import SentenceTransformer
                
                model_path = self._model_name
                # Support PyInstaller : si on est dans un binaire, on cherche le modèle embarqué
                if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
                    # On teste plusieurs emplacements possibles dans le bundle
                    candidates = [
                        Path(sys._MEIPASS) / "models" / self._model_name,
                        Path(sys._MEIPASS) / "everycli" / "data" / "models" / self._model_name,
                    ]
                    for candidate in candidates:
                        if candidate.exists():
                            model_path = str(candidate)
                            break
                
                self._model = SentenceTransformer(model_path)
            except Exception:
                # Environnements sans accès réseau ou sans modèle disponible :
                # on bascule sur un modèle de secours déterministe très léger
                # qui fournit des embeddings basés sur un bag-of-words simple.
                import re
                import unicodedata
                class DummyModel:
                    def __init__(self, dimension=512):
                        self.dimension = dimension

                    def _tokenize(self, text: str) -> list[str]:
                        text = unicodedata.normalize('NFD', text)
                        text = ''.join(ch for ch in text if not unicodedata.combining(ch))
                        tokens = re.findall(r"\w+", text.lower(), flags=re.UNICODE)
                        return tokens

                    def encode(self, texts, convert_to_numpy=True, show_progress_bar=False):
                        import numpy as _np
                        vectors = _np.zeros((len(texts), self.dimension), dtype=_np.float32)
                        for i, t in enumerate(texts):
                            for tok in self._tokenize(t):
                                # Hashing simple pour une dimension stable
                                idx = abs(hash(tok)) % self.dimension
                                vectors[i, idx] += 1.0
                        return vectors

                self._model = DummyModel()

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

    def _compute_cache_key(self, documents: list[str]) -> str:
        # On inclut le nom du modèle dans la clé pour invalider le cache si on change de modèle
        content = json.dumps([self._model_name] + documents, ensure_ascii=False, sort_keys=True)
        return hashlib.md5(content.encode()).hexdigest()

    def fit(self, scenarios: list[Scenario]) -> None:
        if not scenarios:
            return

        self._scenarios = scenarios
        documents = [_scenario_to_document(s) for s in scenarios]
        cache_key = self._compute_cache_key(documents)

        cached = self._load_cache(cache_key)
        if cached is not None:
            self._embeddings = cached
            self._fitted = True
            return  # Cache hit -> On esquive le _load_model() qui coûte 3s

        # Cache miss — on charge le modèle, on encode et on sauvegarde
        self._load_model()
        # On encode en float16 pour économiser 50% de RAM sur les embeddings
        self._embeddings = self._model.encode(
            documents,
            convert_to_numpy=True,
            show_progress_bar=False,
            output_value="sentence_embedding"
        ).astype(np.float16)
        
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

        # Le modèle doit toujours être chargé pour encoder la query
        # (même si les embeddings de la base viennent du cache disque)
        self._load_model()

        expected_dim = self._embeddings.shape[1]

        # Cache de query : valide seulement si la dimension correspond
        query_embedding = self._load_query_cache(query)
        if query_embedding is not None and query_embedding.shape[1] != expected_dim:
            # Cache invalide (ancien DummyModel ou changement de modèle)
            self._query_cache_path(query).unlink(missing_ok=True)
            query_embedding = None

        if query_embedding is None:
            query_embedding = self._model.encode(
                [query],
                convert_to_numpy=True,
                show_progress_bar=False,
            ).astype(np.float16)
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