"""
Interface for clipboard operations.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class ClipboardWriter(Protocol):
    """Responsible for writing text to the system clipboard."""

    def copy(self, text: str) -> bool:
        """
        Copy text to clipboard.
        Returns True on success, False on failure.
        """
        ...
