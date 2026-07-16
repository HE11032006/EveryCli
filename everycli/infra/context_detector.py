"""
ProjectContextDetector — detects the likely command namespace(s) from marker
files in the current working directory (e.g. composer.json -> 'composer').
Pure filesystem check, no network, no heavy import — must stay negligible
compared to the search itself.
"""

from pathlib import Path

from everycli.core.interfaces import ContextDetector as ContextDetectorProtocol

# Maps a marker file/directory found at the project root to the namespace(s)
# it implies. Order matters only for output order, not for correctness.
_MARKERS: dict[str, list[str]] = {
    "composer.json": ["composer"],
    "package.json": ["npm"],
    "pyproject.toml": ["python"],
    "requirements.txt": ["python"],
    "pytest.ini": ["python"],
    ".git": ["git"],
    "docker-compose.yml": ["docker_compose", "docker"],
    "docker-compose.yaml": ["docker_compose", "docker"],
    "Dockerfile": ["docker"],
}


class ProjectContextDetector:
    """Detects the likely command namespace(s) from marker files in the
    current working directory."""

    def __init__(self, cwd: Path | None = None):
        self._cwd = cwd or Path.cwd()

    def detect(self) -> list[str]:
        found: list[str] = []
        for marker, namespaces in _MARKERS.items():
            if (self._cwd / marker).exists():
                for ns in namespaces:
                    if ns not in found:
                        found.append(ns)
        return found


assert isinstance(ProjectContextDetector(), ContextDetectorProtocol), \
    "ProjectContextDetector must implement ContextDetector"
