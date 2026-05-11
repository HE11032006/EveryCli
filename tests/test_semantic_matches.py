"""
Tests for infra/semantic_matcher.py
These tests are slower than the rest — they load a real model.
Marked with 'slow' so they can be skipped in fast CI runs.
"""

import pytest
from everycli.core.models import Command, Scenario
from everycli.infra.semantic_matcher import SemanticMatcher


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
        make("stash", "Mettre mes changements de côté temporairement sans faire de commit", ["git", "stash", "sauvegarder", "temporaire", "travail"]),
        make("reset", "Annuler ou défaire mon dernier commit sans perdre les changements", ["git", "reset", "annuler", "défaire", "revenir"]),
        make("replace", "Remplacer un mot dans tous les commits", ["git", "commit", "remplacer", "chercher", "substitution"]),
    ]


@pytest.mark.slow
class TestSemanticMatcher:
    def test_match_returns_empty_before_fit(self, scenarios):
        matcher = SemanticMatcher()
        assert matcher.match("modifier commit") == []

    def test_fit_with_empty_list_does_not_crash(self):
        matcher = SemanticMatcher()
        matcher.fit([])
        assert matcher.match("quelque chose") == []

    def test_match_returns_results_after_fit(self, scenarios):
        matcher = SemanticMatcher()
        matcher.fit(scenarios)
        results = matcher.match("modifier le dernier commit")
        assert len(results) > 0

    def test_scores_are_between_0_and_1(self, scenarios):
        matcher = SemanticMatcher()
        matcher.fit(scenarios)
        results = matcher.match("commit")
        for _, score in results:
            assert 0.0 <= score <= 1.0

    def test_top_k_limits_results(self, scenarios):
        matcher = SemanticMatcher()
        matcher.fit(scenarios)
        results = matcher.match("git commit", top_k=2)
        assert len(results) <= 2

    def test_semantic_understanding_stash(self, scenarios):
        """
        Le vrai test sémantique — TF-IDF raterait ça.
        La requête ne contient pas le mot 'stash'.
        """
        matcher = SemanticMatcher()
        matcher.fit(scenarios)
        results = matcher.match(
            "je veux sauvegarder mon travail sans faire de commit"
        )
        assert len(results) > 0
        best, _ = results[0]
        assert best.id == "stash"

    def test_semantic_understanding_reset(self, scenarios):
        """
        Requête naturelle sans les mots exacts du scénario.
        """
        matcher = SemanticMatcher()
        matcher.fit(scenarios)
        results = matcher.match("défaire ce que j'ai commité sans perdre mon code")
        best, _ = results[0]
        assert best.id == "reset"