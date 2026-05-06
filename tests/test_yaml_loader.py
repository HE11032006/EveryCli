"""Tests for infra/yaml_loader.py"""

import pytest
from pathlib import Path
import tempfile
import yaml

from everycli.infra.yaml_loader import YamlLoader
from everycli.core.models import Scenario


SAMPLE_YAML = [
    {
        "id": "test_scenario",
        "description": "Un scénario de test",
        "tags": ["test", "git"],
        "commands": {
            "linux": "git status",
            "windows": "git status",
        },
        "explanation": "Affiche l'état du dépôt.",
        "warning": "Aucun",
        "errors": [
            {
                "trigger": "fatal: not a git repo",
                "cause": "Pas dans un dépôt Git",
                "fix": "Fais git init",
            }
        ],
    }
]


@pytest.fixture
def yaml_dir():
    """Crée un dossier temporaire avec un fichier YAML de test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir)
        (path / "test.yaml").write_text(
            yaml.dump(SAMPLE_YAML, allow_unicode=True),
            encoding="utf-8"
        )
        yield path


class TestYamlLoader:
    def test_loads_scenarios_from_directory(self, yaml_dir):
        loader = YamlLoader(yaml_dir)
        scenarios = loader.load_all()
        assert len(scenarios) == 1

    def test_scenario_has_correct_id(self, yaml_dir):
        scenarios = YamlLoader(yaml_dir).load_all()
        assert scenarios[0].id == "test_scenario"

    def test_scenario_has_correct_tags(self, yaml_dir):
        scenarios = YamlLoader(yaml_dir).load_all()
        assert "git" in scenarios[0].tags

    def test_scenario_has_error_hints(self, yaml_dir):
        scenarios = YamlLoader(yaml_dir).load_all()
        assert len(scenarios[0].error_hints) == 1
        assert "git repo" in scenarios[0].error_hints[0].trigger

    def test_empty_directory_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            scenarios = YamlLoader(Path(tmpdir)).load_all()
            assert scenarios == []

    def test_loads_multiple_yaml_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "a.yaml").write_text(
                yaml.dump(SAMPLE_YAML, allow_unicode=True), encoding="utf-8"
            )
            (path / "b.yaml").write_text(
                yaml.dump(SAMPLE_YAML, allow_unicode=True), encoding="utf-8"
            )
            scenarios = YamlLoader(path).load_all()
            assert len(scenarios) == 2