"""
Core interfaces (Protocols) for EveryCLI.

These define the contracts that infra/ implementations must respect.
The core never imports from infra/ — only the other way around.
This is what makes the architecture swappable (TF-IDF → NLP, YAML → DB, etc.)
"""

from typing import Protocol, runtime_checkable
from .models import OS, Scenario, SearchResult


@runtime_checkable
class ScenarioLoader(Protocol):
    """
    Responsible for loading scenarios from any data source.
    Today: YAML files. Tomorrow: database, API, anything.
    """

    def load_all(self) -> list[Scenario]:
        """Load and return all available scenarios."""
        ...


@runtime_checkable
class Matcher(Protocol):
    """
    Responsible for matching a user query to the most relevant scenarios.
    Today: TF-IDF. Phase 2: semantic NLP model.
    Swapping the implementation never touches SearchEngine.
    """

    def fit(self, scenarios: list[Scenario]) -> None:
        """Index the scenarios so they can be searched."""
        ...

    def match(self, query: str, top_k: int = 3) -> list[tuple[Scenario, float]]:
        """
        Return the top_k most relevant scenarios for the query,
        each paired with a relevance score [0.0 - 1.0].
        """
        ...


@runtime_checkable
class OSResolver(Protocol):
    """
    Responsible for detecting the current OS.
    Abstracted so tests can inject a fake resolver without touching sys.platform.
    """

    def resolve(self) -> OS:
        """Detect and return the current operating system."""
        ...


@runtime_checkable
class ResultFormatter(Protocol):
    """
    Responsible for rendering a SearchResult to the terminal.
    Today: Rich (colored terminal). Tomorrow: JSON output, GUI, anything.
    """

    def format(self, result: SearchResult) -> str:
        """Render a search result as a displayable string."""
        ...

    def format_error_hint(self, error_message: str, result: SearchResult) -> str:
        """Render an error hint when the user reports a failed command."""
        ...