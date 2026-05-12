"""
AddEngine — orchestrates adding a new scenario.
Depends only on interfaces — fully testable.
"""

import re
from everycli.core.interfaces import ScenarioWriter
from everycli.core.models import Command, ErrorHint, Scenario


def _slugify(text: str) -> str:
    """Convert a description to a valid scenario id."""
    text = text.lower().strip()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", "_", text)
    return text[:60]


class AddEngine:
    """
    Orchestrates the creation and persistence of a new scenario.
    Receives all data already validated — no I/O here.
    """

    def __init__(self, writer: ScenarioWriter):
        self._writer = writer

    def add(
        self,
        environment: str,
        description: str,
        tags: list[str],
        linux_command: str,
        windows_command: str,
        explanation: str,
        warning: str = "",
        error_hints: list[ErrorHint] | None = None,
    ) -> Scenario:
        """Build a Scenario and persist it. Returns the created scenario."""

        scenario = Scenario(
            id=f"{environment}_{_slugify(description)}",
            description=description,
            tags=[t.strip().lower() for t in tags if t.strip()],
            command=Command(
                linux=linux_command,
                windows=windows_command,
            ),
            explanation=explanation,
            warning=warning,
            error_hints=error_hints or [],
        )

        self._writer.write(scenario, environment)
        return scenario