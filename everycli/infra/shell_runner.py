"""
Shell command runner implementation.
Executes a command in the current shell and returns exit code + output.
"""

import subprocess
import platform

from everycli.core.interfaces import CommandRunner as CommandRunnerProtocol


class ShellRunner:
    """Runs a shell command and captures its output."""

    def run(self, command: str) -> tuple[int, str]:
        """
        Execute a shell command.
        Returns (exit_code, output).
        exit_code 0 means success, anything else is an error.
        """
        is_windows = platform.system() == "Windows"

        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            executable=None if is_windows else "/bin/bash",
        )

        output = result.stdout.strip() or result.stderr.strip()
        return result.returncode, output


assert isinstance(ShellRunner(), CommandRunnerProtocol), \
    "ShellRunner must implement CommandRunnerProtocol"