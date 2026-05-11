"""
DaemonManager — gère le cycle de vie du processus daemon (PID, Start/Stop/Status).
"""

import os
import signal
import sys
from pathlib import Path
from typing import Optional

EVERYCLI_DIR = Path.home() / ".everycli"
PID_FILE     = EVERYCLI_DIR / "daemon.pid"

class DaemonManager:
    def __init__(self, pid_file: Path = PID_FILE):
        self.pid_file = pid_file
        EVERYCLI_DIR.mkdir(parents=True, exist_ok=True)

    def write_pid(self, pid: int):
        self.pid_file.write_text(str(pid), encoding="utf-8")

    def clear_pid(self):
        try:
            self.pid_file.unlink(missing_ok=True)
        except Exception:
            pass

    def read_pid(self) -> Optional[int]:
        try:
            return int(self.pid_file.read_text(encoding="utf-8").strip())
        except Exception:
            return None

    def is_running(self) -> bool:
        pid = self.read_pid()
        if pid is None:
            return False
        try:
            os.kill(pid, 0)
            return True
        except (ProcessLookupError, PermissionError):
            return False

    def stop(self) -> bool:
        pid = self.read_pid()
        if not pid or not self.is_running():
            self.clear_pid()
            return False
        
        try:
            os.kill(pid, signal.SIGTERM)
            return True
        except Exception:
            return False
