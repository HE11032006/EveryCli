from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from everycli.core.models import Command, Scenario, SearchResult
from everycli.everycli import app, available_environments


def test_available_environments_follow_command_files(tmp_path):
    (tmp_path / "composer.yaml").write_text("[]", encoding="utf-8")
    (tmp_path / "docker_compose.yaml").write_text("[]", encoding="utf-8")
    (tmp_path / "notes.txt").write_text("ignored", encoding="utf-8")

    assert available_environments(tmp_path) == ["composer", "docker_compose", "other"]


def test_plan_command_uses_the_local_safety_planner():
    scenario = Scenario(
        id="git_status",
        description="Show repository status",
        tags=["git"],
        command=Command(linux="git status", windows="git status"),
        explanation="Displays the working tree status.",
    )
    search_result = SearchResult(scenario=scenario, resolved_command="git status", score=0.9)
    coordinator = MagicMock()
    coordinator.execute_search.return_value = [search_result]

    with patch("everycli.core.coordinator.SearchCoordinator", return_value=coordinator):
        result = CliRunner().invoke(app, ["plan", "show repository status", "--local"])

    assert result.exit_code == 0
    assert "EveryCli Sentinel" in result.output
    assert "git status" in result.output
    assert "Source : git_status" in result.output
    assert "Planificateur : local" in result.output
