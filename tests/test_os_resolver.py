"""Tests for infra/os_resolver.py"""

from unittest.mock import patch
from everycli.core.models import OS
from everycli.infra.os_resolver import OSResolver


class TestOSResolver:
    def test_detects_linux(self):
        with patch("sys.platform", "linux"):
            assert OSResolver().resolve() == OS.LINUX

    def test_detects_windows(self):
        with patch("sys.platform", "win32"):
            assert OSResolver().resolve() == OS.WINDOWS

    def test_detects_macos(self):
        with patch("sys.platform", "darwin"):
            assert OSResolver().resolve() == OS.MACOS

    def test_unknown_platform_returns_unknown(self):
        with patch("sys.platform", "freebsd"):
            assert OSResolver().resolve() == OS.UNKNOWN