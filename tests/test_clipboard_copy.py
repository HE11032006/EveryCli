"""Tests for infra/clipboard_copy.py"""

from unittest.mock import patch, MagicMock
from everycli.infra.clipboard_copy import ClipboardCopy
import subprocess


class TestClipboardCopy:
    def test_returns_true_on_success_linux(self):
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = ClipboardCopy().copy("git commit --amend")
                assert result is True

    def test_returns_true_on_success_windows(self):
        with patch("platform.system", return_value="Windows"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = ClipboardCopy().copy("git commit --amend")
                assert result is True

    def test_returns_true_on_success_macos(self):
        with patch("platform.system", return_value="Darwin"):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                result = ClipboardCopy().copy("git commit --amend")
                assert result is True

    def test_returns_false_when_tool_not_found(self):
        with patch("platform.system", return_value="Linux"):
            with patch("subprocess.run", side_effect=FileNotFoundError):
                result = ClipboardCopy().copy("git commit --amend")
                assert result is False

    def test_returns_false_on_process_error(self):
        with patch("platform.system", return_value="Windows"):
            with patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(1, "clip"),
            ):
                result = ClipboardCopy().copy("git commit --amend")
                assert result is False