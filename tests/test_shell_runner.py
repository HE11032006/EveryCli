"""Tests for infra/shell_runner.py"""

import pytest
from everycli.infra.shell_runner import ShellRunner


class TestShellRunner:
    def test_successful_command_returns_exit_code_0(self):
        runner = ShellRunner()
        code, _ = runner.run("echo hello")
        assert code == 0

    def test_successful_command_returns_output(self):
        runner = ShellRunner()
        _, output = runner.run("echo hello")
        assert "hello" in output

    def test_failed_command_returns_nonzero_exit_code(self):
        runner = ShellRunner()
        code, _ = runner.run("exit 1")
        assert code != 0

    def test_invalid_command_returns_nonzero_exit_code(self):
        runner = ShellRunner()
        code, _ = runner.run("commande_qui_nexiste_pas_du_tout")
        assert code != 0

    def test_output_is_stripped(self):
        runner = ShellRunner()
        _, output = runner.run("echo   hello   ")
        assert output == "hello"