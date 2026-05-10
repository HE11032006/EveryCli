"""
Clipboard writer implementation.
Copies text to the system clipboard cross-platform.
"""

import platform
import subprocess

from everycli.core.interfaces import ClipboardWriter as ClipboardWriterProtocol


class ClipboardCopy:
    """Copies text to the system clipboard."""

    def copy(self, text: str) -> bool:
        """
        Copy text to clipboard.
        Returns True on success, False on failure.
        """
        system = platform.system()

        try:
            if system == "Windows":
                subprocess.run(
                    ["clip"],
                    input=text.encode("utf-8"),
                    check=True,
                )
            elif system == "Darwin":
                subprocess.run(
                    ["pbcopy"],
                    input=text.encode("utf-8"),
                    check=True,
                )
            else:
                # Linux — essaie xclip puis xsel
                try:
                    subprocess.run(
                        ["xclip", "-selection", "clipboard"],
                        input=text.encode("utf-8"),
                        check=True,
                    )
                except FileNotFoundError:
                    subprocess.run(
                        ["xsel", "--clipboard", "--input"],
                        input=text.encode("utf-8"),
                        check=True,
                    )
            return True

        except (subprocess.CalledProcessError, FileNotFoundError):
            return False


assert isinstance(ClipboardCopy(), ClipboardWriterProtocol), \
    "ClipboardCopy must implement ClipboardWriterProtocol"