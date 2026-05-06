"""
Interface for shell command execution.
"""

from typing import Protocol, runtime_checkable


@runtime_checkable
class CommandRunner(Protocol):
    """Responsible for executing a shell command."""

    def run(self, command: str) -> tuple[int, str]:
        """
        Execute a shell command.
        Returns (exit_code, output).
        """
        ...
