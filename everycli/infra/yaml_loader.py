"""
YAML-based scenario loader.
Reads all .yaml files from a given directory and parses them into Scenario objects.
"""

from pathlib import Path
import yaml

from everycli.core.models import Command, ErrorHint, Scenario
from everycli.core.interfaces import ScenarioLoader as ScenarioLoaderProtocol


class YamlLoader:
    """Loads scenarios from YAML files in a directory."""

    def __init__(self, data_dir: Path):
        self._data_dir = data_dir

    def load_all(self) -> list[Scenario]:
        scenarios = []

        def _extract_entries(data):
            if isinstance(data, list):
                for item in data:
                    yield from _extract_entries(item)
            elif isinstance(data, dict):
                if "id" in data and "description" in data:
                    yield data
                else:
                    for value in data.values():
                        yield from _extract_entries(value)

        for yaml_file in sorted(self._data_dir.glob("*.yaml")):
            raw = yaml_file.read_text(encoding="utf-8")
            try:
                entries = yaml.safe_load(raw)
            except Exception:
                continue

            for entry in _extract_entries(entries):
                try:
                    scenarios.append(self._parse(entry))
                except (KeyError, TypeError):
                    continue

        return scenarios

    def _parse(self, entry: dict) -> Scenario:
        # Supporte deux formats :
        # 1. {commands: {linux: ..., windows: ...}}  (format multi-OS)
        # 2. {command: "..."}                        (format simplifié)
        if "commands" in entry:
            cmd = entry["commands"]
            command = Command(
                linux=cmd.get("linux", ""),
                windows=cmd.get("windows", ""),
                macos=cmd.get("macos", ""),
            )
        else:
            raw_cmd = entry.get("command", "")
            command = Command(linux=raw_cmd, windows=raw_cmd, macos=raw_cmd)

        error_hints = [
            ErrorHint(
                trigger=e["trigger"],
                cause=e["cause"],
                fix=e["fix"],
            )
            for e in entry.get("errors", [])
        ]

        return Scenario(
            id=str(entry["id"]),
            description=str(entry["description"]),
            tags=[str(t) for t in entry.get("tags", [])],
            command=command,
            explanation=str(entry["explanation"]),
            warning=str(entry.get("warning", "")),
            error_hints=error_hints,
        )


assert isinstance(YamlLoader(Path(".")), ScenarioLoaderProtocol), \
    "YamlLoader must implement ScenarioLoaderProtocol"