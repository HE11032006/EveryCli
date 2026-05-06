"""
YAML scenario writer.
Appends a new scenario to the correct YAML file based on environment.
"""

from pathlib import Path
import yaml

from everycli.core.models import Scenario
from everycli.core.interfaces import ScenarioWriter as ScenarioWriterProtocol


class YamlWriter:
    """Appends a new scenario to the correct YAML file."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def write(self, scenario: Scenario, environment: str) -> None:
        target_file = self._data_dir / f"{environment}.yaml"

        entry = self._serialize(scenario)

        existing = []
        if target_file.exists():
            content = target_file.read_text(encoding="utf-8")
            existing = yaml.safe_load(content) or []

        existing.append(entry)

        target_file.write_text(
            yaml.dump(existing, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )

    def _serialize(self, scenario: Scenario) -> dict:
        entry: dict = {
            "id": scenario.id,
            "description": scenario.description,
            "tags": scenario.tags,
            "commands": {
                "linux": scenario.command.linux,
                "windows": scenario.command.windows,
            },
            "explanation": scenario.explanation,
        }

        if scenario.warning:
            entry["warning"] = scenario.warning

        if scenario.error_hints:
            entry["errors"] = [
                {
                    "trigger": h.trigger,
                    "cause": h.cause,
                    "fix": h.fix,
                }
                for h in scenario.error_hints
            ]

        return entry


assert isinstance(YamlWriter(Path(".")), ScenarioWriterProtocol), \
    "YamlWriter must implement ScenarioWriterProtocol"