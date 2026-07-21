from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from everycli.core.models import Command, Scenario, SearchResult
from everycli.everycli import app, available_environments, main
from everycli.infra.daemon_client import DAEMON_RUNNER_ARG


def test_main_calls_start_daemon_directly_for_the_runner_sentinel():
    # Bypasses Typer/Click and Rich entirely — required so a fully detached
    # respawned process (no console, stdio redirected to NUL) doesn't crash
    # trying to print through Rich before the daemon is even up.
    with patch("sys.argv", ["everycli", DAEMON_RUNNER_ARG]), \
         patch("everycli.infra.daemon.start_daemon") as mock_start:
        main()
    mock_start.assert_called_once_with()


def test_main_runs_the_normal_app_for_regular_invocations():
    with patch("sys.argv", ["everycli", "--help"]), \
         patch("everycli.infra.daemon.start_daemon") as mock_start, \
         patch("everycli.everycli.app") as mock_app:
        main()
    mock_start.assert_not_called()
    mock_app.assert_called_once_with()


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

def _shell_search_result():
    scenario = Scenario(
        id="git_status",
        description="Show repository status",
        tags=["git"],
        command=Command(linux="git status", windows="git status"),
        explanation="Displays the working tree status.",
        namespace="git",
    )
    return SearchResult(scenario=scenario, resolved_command="git status", score=0.9)


def test_shell_mode_emits_only_the_confirmed_command_on_stdout():
    coordinator = MagicMock()
    coordinator.execute_search.return_value = [_shell_search_result()]
    history = MagicMock()

    with patch("everycli.core.coordinator.SearchCoordinator", return_value=coordinator), \
         patch("everycli.everycli._get_history_manager", return_value=history), \
         patch("everycli.everycli.Confirm.ask", return_value=True), \
         patch("everycli.everycli.console"):
        result = CliRunner().invoke(app, ["search", "repository status", "-s", "--no-daemon"])

    assert result.exit_code == 0
    assert "git status" in result.stdout
    assert "git status" in result.stderr

