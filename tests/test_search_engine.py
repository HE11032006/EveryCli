"""Tests for core/search_engine.py — uses fakes, zero real I/O."""

import pytest
from everycli.core.models import Command, OS, Scenario, SearchResult
from everycli.core.search_engine import SearchEngine


# ── Fakes ────────────────────────────────────────────────────────────────────

class FakeLoader:
    def __init__(self, scenarios):
        self._scenarios = scenarios

    def load_all(self):
        return self._scenarios


class FakeMatcher:
    def __init__(self, results):
        self._results = results  # list[tuple[Scenario, float]]

    def fit(self, scenarios):
        pass

    def match(self, query, top_k=3):
        return self._results[:top_k]


class FakeOSResolver:
    def __init__(self, os):
        self._os = os

    def resolve(self):
        return self._os


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def scenario():
    return Scenario(
        id="test",
        description="Test scenario",
        tags=["test"],
        command=Command(linux="echo linux", windows="echo windows"),
        explanation="Just a test.",
    )


@pytest.fixture
def engine(scenario):
    loader = FakeLoader([scenario])
    matcher = FakeMatcher([(scenario, 0.9)])
    resolver = FakeOSResolver(OS.LINUX)
    return SearchEngine(loader, matcher, resolver)


# ── Tests ─────────────────────────────────────────────────────────────────────

class TestSearchEngine:
    def test_raises_if_search_called_before_boot(self, engine):
        with pytest.raises(RuntimeError, match="boot()"):
            engine.search("anything")

    def test_returns_results_after_boot(self, engine):
        engine.boot()
        results = engine.search("test")
        assert len(results) == 1

    def test_result_is_search_result_instance(self, engine):
        engine.boot()
        results = engine.search("test")
        assert isinstance(results[0], SearchResult)

    def test_resolves_linux_command_on_linux(self, scenario):
        engine = SearchEngine(
            FakeLoader([scenario]),
            FakeMatcher([(scenario, 0.9)]),
            FakeOSResolver(OS.LINUX),
        )
        engine.boot()
        result = engine.search("test")[0]
        assert result.resolved_command == "echo linux"

    def test_resolves_windows_command_on_windows(self, scenario):
        engine = SearchEngine(
            FakeLoader([scenario]),
            FakeMatcher([(scenario, 0.9)]),
            FakeOSResolver(OS.WINDOWS),
        )
        engine.boot()
        result = engine.search("test")[0]
        assert result.resolved_command == "echo windows"

    def test_score_is_preserved_in_result(self, engine):
        engine.boot()
        result = engine.search("test")[0]
        assert result.score == 0.9

    def test_empty_matcher_returns_empty_results(self, scenario):
        engine = SearchEngine(
            FakeLoader([scenario]),
            FakeMatcher([]),
            FakeOSResolver(OS.LINUX),
        )
        engine.boot()
        assert engine.search("anything") == []