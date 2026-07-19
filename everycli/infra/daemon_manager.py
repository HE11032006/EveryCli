"""Cross-platform daemon PID lifecycle helpers."""

import os
import signal
import subprocess
from pathlib import Path
from typing import Optional

EVERYCLI_DIR = Path.home() / ".everycli"
PID_FILE = EVERYCLI_DIR / "daemon.pid"


def _windows_process_is_running(pid: int) -> bool:
    """Return whether a process can be opened on Windows."""
    try:
        import ctypes
        from ctypes import wintypes
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.OpenProcess.argtypes = (wintypes.DWORD, wintypes.BOOL, wintypes.DWORD)
        kernel32.OpenProcess.restype = wintypes.HANDLE
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.OpenProcess(0x1000, False, pid)
        if not handle:
            return False
        try:
            return True
        finally:
            kernel32.CloseHandle(handle)
    except OSError:
        return False


def _pid_is_running(pid: int) -> bool:
    if os.name == "nt":
        return _windows_process_is_running(pid)
    try:
        os.kill(pid, 0)
        return True
    except (ProcessLookupError, PermissionError, OSError):
        return False


class DaemonManager:
    def __init__(self, pid_file: Path = PID_FILE):
        self.pid_file = pid_file
        self.pid_file.parent.mkdir(parents=True, exist_ok=True)

    def write_pid(self, pid: int):
        self.pid_file.write_text(str(pid), encoding="utf-8")

    def clear_pid(self):
        try:
            self.pid_file.unlink(missing_ok=True)
        except OSError:
            pass

    def read_pid(self) -> Optional[int]:
        try:
            return int(self.pid_file.read_text(encoding="utf-8").strip())
        except (OSError, ValueError):
            return None

    def is_running(self) -> bool:
        pid = self.read_pid()
        if pid is None:
            return False
        running = _pid_is_running(pid)
        if not running:
            self.clear_pid()
        return running

    def stop(self) -> bool:
        pid = self.read_pid()
        if not pid or not self.is_running():
            self.clear_pid()
            return False
        try:
            if os.name == "nt":
                result = subprocess.run(["taskkill", "/PID", str(pid), "/T"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
                stopped = result.returncode == 0
            else:
                os.kill(pid, signal.SIGTERM)
                stopped = True
        except OSError:
            stopped = False
        if stopped:
            self.clear_pid()
        return stopped
