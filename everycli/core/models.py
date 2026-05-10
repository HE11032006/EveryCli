"""
Core domain models for EveryCLI.
Pure dataclasses — no external dependencies, no side effects.
"""

from dataclasses import dataclass, field
from enum import Enum


class OS(Enum):
    LINUX = "linux"
    WINDOWS = "windows"
    MACOS = "macos"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class Command:
    """A platform-specific command."""
    linux: str
    windows: str
    macos: str = ""

    def for_os(self, os: OS) -> str:
        if os == OS.WINDOWS:
            return self.windows
        if os == OS.MACOS:
            return self.macos or self.linux  # macos fallback vers linux
        return self.linux


@dataclass(frozen=True)
class ErrorHint:
    """A known error with its probable cause and fix."""
    trigger: str   # le message d'erreur qui déclenche ce hint
    cause: str     # explication humaine de la cause
    fix: str       # commande ou action corrective


@dataclass(frozen=True)
class Scenario:
    """
    A single CLI scenario: what the user wants to do,
    how to do it, and what can go wrong.
    """
    id: str
    description: str
    tags: list[str]
    command: Command
    explanation: str
    warning: str = ""
    error_hints: list[ErrorHint] = field(default_factory=list)


@dataclass(frozen=True)
class SearchResult:
    """
    What EveryCLI returns to the user after a search.
    Carries the scenario + the resolved command for the current OS.
    """
    scenario: Scenario
    resolved_command: str  # commande déjà résolue pour l'OS courant
    score: float           # score de pertinence [0.0 - 1.0]

    @property
    def has_warning(self) -> bool:
        return bool(self.scenario.warning)

    def hint_for_error(self, error_message: str) -> ErrorHint | None:
        """Retourne le hint correspondant à un message d'erreur, si trouvé."""
        error_lower = error_message.lower()
        for hint in self.scenario.error_hints:
            if hint.trigger.lower() in error_lower:
                return hint
        return None