"""Tests for core/add_engine.py"""

import pytest
from everycli.core.add_engine import AddEngine, _slugify
from everycli.core.models import Scenario


class FakeWriter:
    def __init__(self):
        self.written: list[tuple[Scenario, str]] = []

    def write(self, scenario: Scenario, environment: str) -> None:
        self.written.append((scenario, environment))


class TestSlugify:
    def test_lowercases(self):
        assert _slugify("GIT COMMIT") == "git_commit"

    def test_replaces_spaces_with_underscores(self):
        assert _slugify("modifier un commit") == "modifier_un_commit"

    def test_removes_special_chars(self):
        assert _slugify("commit: message!") == "commit_message"

    def test_truncates_to_60_chars(self):
        long = "a" * 100
        assert len(_slugify(long)) <= 60


class TestAddEngine:
    @pytest.fixture
    def writer(self):
        return FakeWriter()

    @pytest.fixture
    def engine(self, writer):
        return AddEngine(writer)

    def test_add_calls_writer(self, engine, writer):
        engine.add(
            environment="git",
            description="Tester quelque chose",
            tags=["git", "test"],
            linux_command="git test",
            windows_command="git test",
            explanation="Explication test.",
        )
        assert len(writer.written) == 1

    def test_scenario_id_contains_environment(self, engine, writer):
        engine.add(
            environment="docker",
            description="Lancer un conteneur",
            tags=["docker"],
            linux_command="docker run",
            windows_command="docker run",
            explanation="Lance un conteneur.",
        )
        scenario, env = writer.written[0]
        assert scenario.id.startswith("docker_")
        assert env == "docker"

    def test_tags_are_stripped_and_lowercased(self, engine, writer):
        engine.add(
            environment="git",
            description="test",
            tags=["  GIT  ", "COMMIT ", ""],
            linux_command="git commit",
            windows_command="git commit",
            explanation="test",
        )
        scenario, _ = writer.written[0]
        assert "git" in scenario.tags
        assert "commit" in scenario.tags
        assert "" not in scenario.tags

    def test_empty_warning_not_set(self, engine, writer):
        engine.add(
            environment="git",
            description="test",
            tags=["git"],
            linux_command="git status",
            windows_command="git status",
            explanation="test",
        )
        scenario, _ = writer.written[0]
        assert scenario.warning == ""

    def test_returns_created_scenario(self, engine):
        result = engine.add(
            environment="git",
            description="Voir le statut",
            tags=["git", "status"],
            linux_command="git status",
            windows_command="git status",
            explanation="Affiche le statut du dépôt.",
        )
        assert isinstance(result, Scenario)
        assert result.description == "Voir le statut"