import json
import os
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path.home() / ".everycli" / "history.json"

class History:
    """Manages search history for EveryCli."""

    def __init__(self, history_file: Path = HISTORY_FILE):
        self._file = history_file
        self._ensure_file()

    def _ensure_file(self):
        self._file.parent.mkdir(parents=True, exist_ok=True)
        if not self._file.exists():
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def save(self, query: str):
        """Save a query to history."""
        try:
            history = self.load()
            # Supprime la query si elle existe déjà pour la remettre au début
            if query in history:
                history.remove(query)
            
            history.insert(0, query)
            # On garde seulement les 50 dernières recherches
            history = history[:50]

            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass # L'historique n'est pas critique

    def load(self) -> list[str]:
        """Load history from file."""
        try:
            if not self._file.exists():
                return []
            with open(self._file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []

    def clear(self):
        """Clear history."""
        if self._file.exists():
            self._file.unlink()
        self._ensure_file()
