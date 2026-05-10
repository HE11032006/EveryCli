"""Tests for infra/hybrid_matcher.py — uses fakes, no real models."""

import pytest
from everycli.core.models import Command, Scenario
from everycli.infra.hybrid_matcher import HybridMatcher


# ── Fakes ─────────────────────────────────────────────────────────────────────

class FakeMatcher:
    def __init__(self, results: list, top_score: float = 0.0):
        self._results = results
        self.fitted = False

    def fit(self, scenarios):
        self.fitted = True

    def match(self, query, top_k=3):
        return self._results[:top_k]


@pytest.fixture
def scenarios():
    def make(id, description, tags):
        return Scenario(
            id=id,
            description=description,
            tags=tags,
            command=Command(linux=f"git {id}", windows=f"git {id}"),
            explanation=f"Explication {id}",
        )
    return [
        make("amend", "Modifier le message du dernier commit", ["git", "commit"]),
        make("stash", "Mettre mes changements de côté", ["git", "stash"]),
    ]


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestHybridMatcher:
    def test_returns_empty_before_fit(self, scenarios):
        matcher = HybridMatcher()
        assert matcher.match("commit") == []

    def test_fit_calls_both_matchers(self, scenarios, monkeypatch):
        tfidf_fake = FakeMatcher([])
        semantic_fake = FakeMatcher([])

        matcher = HybridMatcher()
        monkeypatch.setattr(matcher, "_tfidf", tfidf_fake)
        monkeypatch.setattr(matcher, "_semantic", semantic_fake)

        matcher.fit(scenarios)

        assert tfidf_fake.fitted
        assert semantic_fake.fitted

    def test_fast_path_when_tfidf_confident(self, scenarios, monkeypatch):
        best = scenarios[0]
        tfidf_fake = FakeMatcher([(best, 0.9)])
        semantic_fake = FakeMatcher([])

        matcher = HybridMatcher(fast_threshold=0.45)
        monkeypatch.setattr(matcher, "_tfidf", tfidf_fake)
        monkeypatch.setattr(matcher, "_semantic", semantic_fake)
        matcher._fitted = True
        matcher._scenarios = scenarios

        results = matcher.match("modifier commit")

        assert results[0][0].id == "amend"
        assert matcher.used_semantic is False

    def test_slow_path_when_tfidf_not_confident(self, scenarios, monkeypatch):
        best = scenarios[1]
        tfidf_fake = FakeMatcher([(best, 0.1)])
        semantic_fake = FakeMatcher([(best, 0.8)])

        matcher = HybridMatcher(fast_threshold=0.45)
        monkeypatch.setattr(matcher, "_tfidf", tfidf_fake)
        monkeypatch.setattr(matcher, "_semantic", semantic_fake)
        matcher._fitted = True
        matcher._scenarios = scenarios

        results = matcher.match("sauvegarder sans commiter")

        assert matcher.used_semantic is True
        assert len(results) > 0

    def test_used_semantic_false_by_default(self, scenarios, monkeypatch):
        matcher = HybridMatcher()
        monkeypatch.setattr(matcher, "_tfidf", FakeMatcher([(scenarios[0], 0.9)]))
        monkeypatch.setattr(matcher, "_semantic", FakeMatcher([]))
        matcher._fitted = True
        matcher._scenarios = scenarios

        matcher.match("test")
        assert matcher.used_semantic is False

    def test_scores_are_rounded(self, scenarios, monkeypatch):
        best = scenarios[0]
        tfidf_fake = FakeMatcher([(best, 0.123456789)])
        semantic_fake = FakeMatcher([(best, 0.987654321)])

        matcher = HybridMatcher(fast_threshold=0.45)
        monkeypatch.setattr(matcher, "_tfidf", tfidf_fake)
        monkeypatch.setattr(matcher, "_semantic", semantic_fake)
        matcher._fitted = True
        matcher._scenarios = scenarios

        results = matcher.match("test")
        if results:
            _, score = results[0]
            assert score == round(score, 4)