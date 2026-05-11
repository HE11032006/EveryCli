"""Tests for infra/tfidf_matcher.py"""

import pytest
from everycli.core.models import Command, Scenario
from everycli.infra.tfidf_matcher import TFIDFMatcher, _normalize


@pytest.fixture
def scenarios():
    def make(id, description, tags):
        return Scenario(
            id=id,
            description=description,
            tags=tags,
            command=Command(linux=f"git {id}", windows=f"git {id}"),
            explanation=f"Explication pour {id}",
        )

    return [
        make("amend", "Modifier le message du dernier commit", ["git", "commit", "modifier", "amend", "message"]),
        make("stash", "Mettre mes changements de côté", ["git", "stash", "sauvegarder", "temporaire"]),
        make("reset", "Annuler mon dernier commit sans perdre les changements", ["git", "reset", "annuler", "soft"]),
        make("replace", "Remplacer un mot dans tous les commits", ["git", "commit", "remplacer", "historique"]),
    ]


class TestNormalize:
    def test_lowercases_text(self):
        assert _normalize("GIT COMMIT") == "git commit"

    def test_removes_accents(self):
        assert _normalize("éàü") == "eau"

    def test_removes_punctuation(self):
        assert _normalize("git --amend") == "git amend"

    def test_handles_empty_string(self):
        assert _normalize("") == ""


class TestTFIDFMatcher:
    def test_match_returns_empty_before_fit(self, scenarios):
        matcher = TFIDFMatcher()
        assert matcher.match("modifier commit") == []

    def test_fit_with_empty_list_does_not_crash(self):
        matcher = TFIDFMatcher()
        matcher.fit([])
        assert matcher.match("quelque chose") == []

    def test_match_returns_results_after_fit(self, scenarios):
        matcher = TFIDFMatcher()
        matcher.fit(scenarios)
        results = matcher.match("modifier le dernier commit")
        assert len(results) > 0

    def test_best_match_for_amend_query(self, scenarios):
        matcher = TFIDFMatcher()
        matcher.fit(scenarios)
        results = matcher.match("modifier message du dernier commit")
        best, score = results[0]
        assert best.id == "amend"

    def test_best_match_for_stash_query(self, scenarios):
        matcher = TFIDFMatcher()
        matcher.fit(scenarios)
        results = matcher.match("mettre changements de cote temporairement")
        best, _ = results[0]
        assert best.id == "stash"

    def test_best_match_for_reset_query(self, scenarios):
        matcher = TFIDFMatcher()
        matcher.fit(scenarios)
        results = matcher.match("annuler commit sans perdre")
        best, _ = results[0]
        assert best.id == "reset"

    def test_scores_are_between_0_and_1(self, scenarios):
        matcher = TFIDFMatcher()
        matcher.fit(scenarios)
        results = matcher.match("commit")
        for _, score in results:
            assert 0.0 <= score <= 1.0

    def test_top_k_limits_results(self, scenarios):
        matcher = TFIDFMatcher()
        matcher.fit(scenarios)
        results = matcher.match("git commit", top_k=2)
        assert len(results) <= 2

    def test_irrelevant_query_returns_empty(self, scenarios):
        matcher = TFIDFMatcher()
        matcher.fit(scenarios)
        results = matcher.match("kubernetes ingress controller")
        assert results == []