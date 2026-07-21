"""Regression tests for the offline semantic fallback.

No real model is downloaded: a failing SentenceTransformer constructor simulates
an offline first run, which must still let EveryCli search its local corpus.
"""

import sys
import types

from everycli.core.models import Command, Scenario
from everycli.infra.semantic_matcher import SemanticMatcher


def test_offline_fallback_accepts_fit_output_value_and_returns_matches(monkeypatch, tmp_path):
    class BrokenSentenceTransformer:
        def __init__(self, *args, **kwargs):
            raise OSError("model unavailable")

    fake_module = types.SimpleNamespace(SentenceTransformer=BrokenSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)
    matcher = SemanticMatcher(cache_dir=tmp_path)
    scenario = Scenario(
        id="stash",
        description="Save work for later",
        tags=["git", "stash", "temporary"],
        command=Command(linux="git stash", windows="git stash"),
        explanation="Stores uncommitted changes.",
    )

    matcher.fit([scenario])
    results = matcher.match("save my temporary work")

    assert results
    assert results[0][0].id == "stash"


def test_everycli_model_path_env_var_overrides_the_default_model(monkeypatch, tmp_path):
    recorded_paths = []

    class RecordingSentenceTransformer:
        def __init__(self, model_path, *args, **kwargs):
            recorded_paths.append(model_path)

        def encode(self, texts, **kwargs):
            import numpy as np
            return np.zeros((len(texts), 4), dtype=np.float32)

    fake_module = types.SimpleNamespace(SentenceTransformer=RecordingSentenceTransformer)
    monkeypatch.setitem(sys.modules, "sentence_transformers", fake_module)

    override_dir = tmp_path / "everycli-minilm-ft"
    override_dir.mkdir()
    monkeypatch.setenv("EVERYCLI_MODEL_PATH", str(override_dir))

    matcher = SemanticMatcher(cache_dir=tmp_path / "cache")
    scenario = Scenario(
        id="stash",
        description="Save work for later",
        tags=["git", "stash"],
        command=Command(linux="git stash", windows="git stash"),
        explanation="Stores uncommitted changes.",
    )
    matcher.fit([scenario])

    assert recorded_paths == [str(override_dir)]
