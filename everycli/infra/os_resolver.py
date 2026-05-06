"""
OS detection implementation.
Depends on sys.platform only — no external libraries.
"""

import sys
from everycli.core.models import OS
from everycli.core.interfaces import OSResolver as OSResolverProtocol


class OSResolver:
    """Detects the current OS using sys.platform."""

    def resolve(self) -> OS:
        platform = sys.platform

        if platform.startswith("win"):
            return OS.WINDOWS
        if platform.startswith("darwin"):
            return OS.MACOS
        if platform.startswith("linux"):
            return OS.LINUX

        return OS.UNKNOWN


assert isinstance(OSResolver(), OSResolverProtocol), \
    "OSResolver must implement OSResolverProtocol"