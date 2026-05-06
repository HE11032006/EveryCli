"""
Tests for core/models.py and core/interfaces.py

TDD : these tests define the expected behavior.
No external dependencies — pure unit tests.
"""

import pytest
from everycli.core.models import OS, Command, ErrorHint, Scenario, SearchResult
from everycli.core.interfaces import ScenarioLoader, Matcher, OSResolver, ResultFormatter


# ─────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────

@pytest.fixture
def sample_command():
    return Command(
        linux="git filter-branch --msg-filter 'sed s/old/new/g' -- --all",
        windows='git filter-branch --msg-filter "sed s/old/new/g" -- --all',
        macos="git filter-branch --msg-filter 'sed s/old/new/g' -- --all",
    )


@pytest.fixture
def sample_error_hint():
    return ErrorHint(
        trigger="fatal: bad revision",
        cause="Tu n'es pas dans un dépôt Git",
        fix="Vérifie avec : git status",
    )


@pytest.fixture
def sample_scenario(sample_command, sample_error_hint):
    return Scenario(
        id="git_replace_in_commits",
        description="Remplacer un mot dans tous les messages de commits",
        tags=["git", "commit", "remplacer", "historique", "message"],
        command=sample_command,
        explanation="Réécrit l'historique. Un force push sera nécessaire.",
        warning="Modifie l'historique partagé, préviens ton équipe.",
        error_hints=[sample_error_hint],
    )


@pytest.fixture
def sample_result(sample_scenario):
    return SearchResult(
        scenario=sample_scenario,
        resolved_command="git filter-branch --msg-filter 'sed s/old/new/g' -- --all",
        score=0.92,
    )


# ─────────────────────────────────────────────
# Command tests
# ─────────────────────────────────────────────

class TestCommand:
    def test_returns_linux_command_for_linux_os(self, sample_command):
        assert "sed" in sample_command.for_os(OS.LINUX)

    def test_returns_windows_command_for_windows_os(self, sample_command):
        result = sample_command.for_os(OS.WINDOWS)
        assert result == sample_command.windows

    def test_macos_falls_back_to_linux_when_empty(self):
        cmd = Command(linux="ls -la", windows="dir")
        assert cmd.for_os(OS.MACOS) == "ls -la"

    def test_macos_uses_own_command_when_provided(self, sample_command):
        assert sample_command.for_os(OS.MACOS) == sample_command.macos

    def test_command_is_immutable(self, sample_command):
        with pytest.raises(Exception):
            sample_command.linux = "something else"  # type: ignore


# ─────────────────────────────────────────────
# Scenario tests
# ─────────────────────────────────────────────

class TestScenario:
    def test_scenario_has_required_fields(self, sample_scenario):
        assert sample_scenario.id
        assert sample_scenario.description
        assert len(sample_scenario.tags) > 0
        assert sample_scenario.command is not None
        assert sample_scenario.explanation

    def test_scenario_is_immutable(self, sample_scenario):
        with pytest.raises(Exception):
            sample_scenario.id = "new_id"  # type: ignore

    def test_scenario_default_no_warning(self, sample_command):
        scenario = Scenario(
            id="test",
            description="test",
            tags=["test"],
            command=sample_command,
            explanation="test",
        )
        assert scenario.warning == ""

    def test_scenario_default_no_error_hints(self, sample_command):
        scenario = Scenario(
            id="test",
            description="test",
            tags=["test"],
            command=sample_command,
            explanation="test",
        )
        assert scenario.error_hints == []


# ─────────────────────────────────────────────
# SearchResult tests
# ─────────────────────────────────────────────

class TestSearchResult:
    def test_has_warning_when_warning_present(self, sample_result):
        assert sample_result.has_warning is True

    def test_has_no_warning_when_empty(self, sample_scenario, sample_command):
        scenario_no_warning = Scenario(
            id="test",
            description="test",
            tags=["test"],
            command=sample_command,
            explanation="test",
        )
        result = SearchResult(
            scenario=scenario_no_warning,
            resolved_command="git status",
            score=0.8,
        )
        assert result.has_warning is False

    def test_hint_for_error_returns_correct_hint(self, sample_result):
        hint = sample_result.hint_for_error("fatal: bad revision")
        assert hint is not None
        assert "dépôt Git" in hint.cause

    def test_hint_for_error_is_case_insensitive(self, sample_result):
        hint = sample_result.hint_for_error("FATAL: BAD REVISION")
        assert hint is not None

    def test_hint_for_error_returns_none_when_no_match(self, sample_result):
        hint = sample_result.hint_for_error("permission denied")
        assert hint is None

    def test_result_is_immutable(self, sample_result):
        with pytest.raises(Exception):
            sample_result.score = 0.5  # type: ignore


# ─────────────────────────────────────────────
# Interface compliance tests (duck typing via Protocol)
# ─────────────────────────────────────────────

class TestInterfaces:
    """
    Vérifie que les Protocols sont bien définis comme attendu.
    Les vraies implémentations seront testées dans leurs propres fichiers.
    """

    def test_scenario_loader_is_a_protocol(self):
        assert hasattr(ScenarioLoader, 'load_all')

    def test_matcher_is_a_protocol(self):
        assert hasattr(Matcher, 'fit')
        assert hasattr(Matcher, 'match')

    def test_os_resolver_is_a_protocol(self):
        assert hasattr(OSResolver, 'resolve')

    def test_result_formatter_is_a_protocol(self):
        assert hasattr(ResultFormatter, 'format')
        assert hasattr(ResultFormatter, 'format_error_hint')

    def test_a_class_implementing_matcher_protocol(self):
        """Une fausse implémentation doit satisfaire le Protocol."""
        class FakeMatcher:
            def fit(self, scenarios: list) -> None:
                pass
            def match(self, query: str, top_k: int = 3) -> list:
                return []

        assert isinstance(FakeMatcher(), Matcher)

    def test_a_class_implementing_loader_protocol(self):
        class FakeLoader:
            def load_all(self) -> list:
                return []

        assert isinstance(FakeLoader(), ScenarioLoader)