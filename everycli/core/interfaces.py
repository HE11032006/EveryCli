"""
Core interfaces (Protocols) for EveryCLI.
"""

from typing import Protocol, runtime_checkable
from .models import OS, Scenario, SearchResult


@runtime_checkable
class ScenarioLoader(Protocol):
    def load_all(self) -> list[Scenario]: ...


@runtime_checkable
class ScenarioWriter(Protocol):
    """Responsible for persisting a new scenario to a data source."""
    def write(self, scenario: Scenario, environment: str) -> None: ...


@runtime_checkable
class Matcher(Protocol):
    def fit(self, scenarios: list[Scenario]) -> None: ...
    def match(self, query: str, top_k: int = 3) -> list[tuple[Scenario, float]]: ...


@runtime_checkable
class OSResolver(Protocol):
    def resolve(self) -> OS: ...


@runtime_checkable
class ResultFormatter(Protocol):
    def format(self, result: SearchResult) -> str: ...
    def format_error_hint(self, error_message: str, result: SearchResult) -> str: ...


from .command_runner import CommandRunner
from .clipboard import ClipboardWriter