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
            return self.macos or self.linux
        return self.linux

    def to_dict(self) -> dict:
        return {"linux": self.linux, "windows": self.windows, "macos": self.macos}


@dataclass(frozen=True)
class ErrorHint:
    """A known error with its probable cause and fix."""
    trigger: str
    cause: str
    fix: str

    def to_dict(self) -> dict:
        return {"trigger": self.trigger, "cause": self.cause, "fix": self.fix}


@dataclass(frozen=True)
class Scenario:
    """A single CLI scenario."""
    id: str
    description: str
    tags: list[str]
    command: Command
    explanation: str
    warning: str = ""
    error_hints: list[ErrorHint] = field(default_factory=list)
    namespace: str = ""
    """
    The ecosystem this scenario belongs to (git, docker, composer, npm...).
    Always derived from the source YAML filename — never from tags or id —
    so it's guaranteed present and consistent, unlike free-text tags.
    """

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "description": self.description,
            "tags": self.tags,
            "command": self.command.to_dict(),
            "explanation": self.explanation,
            "warning": self.warning,
            "errors": [e.to_dict() for e in self.error_hints],
            "namespace": self.namespace,
        }


@dataclass(frozen=True)
class SearchResult:
    """What EveryCLI returns after a search."""
    scenario: Scenario
    resolved_command: str
    score: float

    def to_dict(self) -> dict:
        return {
            "scenario": self.scenario.to_dict(),
            "resolved_command": self.resolved_command,
            "score": self.score
        }

    @property
    def has_warning(self) -> bool:
        return bool(self.scenario.warning)

    def hint_for_error(self, error_message: str) -> ErrorHint | None:
        error_lower = error_message.lower()
        for hint in self.scenario.error_hints:
            if hint.trigger.lower() in error_lower:
                return hint
        return None