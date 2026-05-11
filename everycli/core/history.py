import json
import os
from datetime import datetime
from pathlib import Path

HISTORY_FILE = Path.home() / ".everycli" / "history.json"

class History:
    """Gère l'historique des recherches et des commandes associées pour EveryCli."""

    def __init__(self, history_file: Path = HISTORY_FILE):
        self._file = history_file
        self._ensure_file()

    def _ensure_file(self):
        self._file.parent.mkdir(parents=True, exist_ok=True)
        if not self._file.exists():
            with open(self._file, "w", encoding="utf-8") as f:
                json.dump([], f)

    def save(self, query: str, description: str = "", command: str = ""):
        """
        Enregistre une recherche. Si une commande est fournie, elle est associée à la recherche.
        """
        try:
            history = self.load()
            
            # Création de l'entrée
            entry = {
                "query": query,
                "description": description,
                "command": command,
                "timestamp": datetime.now().isoformat()
            }

            # Supprime l'ancienne entrée pour la même query pour éviter les doublons
            history = [e for e in history if e["query"] != query]
            
            history.insert(0, entry)
            # On garde les 50 dernières
            history = history[:50]

            with open(self._file, "w", encoding="utf-8") as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def load(self) -> list[dict]:
        """Charge l'historique complet (liste de dictionnaires)."""
        try:
            if not self._file.exists():
                return []
            with open(self._file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Migration auto : si c'est une liste de strings, on convertit
                if data and isinstance(data[0], str):
                    return [{"query": q, "description": "", "command": "", "timestamp": ""} for q in data]
                return data
        except Exception:
            return []

    def clear(self):
        """Vide l'historique."""
        if self._file.exists():
            self._file.unlink()
        self._ensure_file()
