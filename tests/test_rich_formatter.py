"""Tests for infra/rich_formatter.py — vérifie la logique, pas les couleurs."""

import pytest
from io import StringIO
from rich.console import Console

from everycli.core.models import Command, ErrorHint, Scenario, SearchResult, OS
from everycli.infra.rich_formatter import RichFormatter


@pytest.fixture
def scenario():
    return Scenario(
        id="test",
        description="Modifier le dernier commit",
        tags=["git", "commit", "amend"],
        command=Command(linux="git commit --amend", windows="git commit --amend"),
        explanation="Modifie le message du dernier commit.",
        warning="Force push nécessaire si déjà pushé.",
        error_hints=[
            ErrorHint(
                trigger="nothing to commit",
                cause="Aucun fichier en staging",
                fix="git add <fichier>",
            )
        ],
    )


@pytest.fixture
def result(scenario):
    return SearchResult(
        scenario=scenario,
        resolved_command="git commit --amend",
        score=0.92,
    )


class TestRichFormatter:
    def _capture(self, fn) -> str:
        """Helper : capture Rich output to string."""
        buffer = StringIO()
        capture_console = Console(file=buffer, highlight=False)
        original = RichFormatter()
        # on remplace temporairement le console global
        import everycli.infra.rich_formatter as mod
        original_console = mod.console
        mod.console = capture_console
        fn(original)
        mod.console = original_console
        return buffer.getvalue()

    def test_format_contains_command(self, result):
        output = self._capture(lambda f: f.format(result))
        assert "git commit --amend" in output

    def test_format_contains_explanation(self, result):
        output = self._capture(lambda f: f.format(result))
        assert "Modifie le message" in output

    def test_format_contains_warning(self, result):
        output = self._capture(lambda f: f.format(result))
        assert "Force push" in output

    def test_format_contains_score(self, result):
        output = self._capture(lambda f: f.format(result))
        assert "92%" in output

    def test_format_error_hint_known_error(self, result):
        output = self._capture(
            lambda f: f.format_error_hint("nothing to commit", result)
        )
        assert "Aucun fichier en staging" in output
        assert "git add" in output

    def test_format_error_hint_unknown_error(self, result):
        output = self._capture(
            lambda f: f.format_error_hint("permission denied", result)
        )
        assert "non reconnue" in output