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

    def test_scenario_namespace_matches_filename(self, yaml_dir):
        """The namespace must come from the source filename (test.yaml -> 'test'),
        not from tags or the id, so it's always present and reliable."""
        scenarios = YamlLoader(yaml_dir).load_all()
        assert scenarios[0].namespace == "test"

    def test_different_files_produce_different_namespaces(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "docker.yaml").write_text(
                yaml.dump(SAMPLE_YAML, allow_unicode=True), encoding="utf-8"
            )
            (path / "composer.yaml").write_text(
                yaml.dump(SAMPLE_YAML, allow_unicode=True), encoding="utf-8"
            )
            scenarios = YamlLoader(path).load_all()
            namespaces = {s.namespace for s in scenarios}
            assert namespaces == {"docker", "composer"}

    def test_entry_without_kind_is_treated_as_command(self, yaml_dir):
        """Backward compat: existing entries have no `kind` field at all."""
        scenarios = YamlLoader(yaml_dir).load_all()
        assert len(scenarios) == 1
        assert scenarios[0].id == "test_scenario"

    def test_tip_entries_are_skipped_not_dropped_as_errors(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            data = [
                {**SAMPLE_YAML[0], "id": "real_command"},
                {
                    "id": "some_tip",
                    "kind": "tip",
                    "description": "Une astuce",
                    "tags": ["astuce"],
                    "content": "Faites ceci plutôt que cela.",
                },
            ]
            (path / "mixed.yaml").write_text(
                yaml.dump(data, allow_unicode=True), encoding="utf-8"
            )
            import logging
            with caplog.at_level(logging.WARNING):
                scenarios = YamlLoader(path).load_all()

            # Le tip n'est pas un Scenario (il n'a pas de commande) mais son
            # absence ne doit PAS ressembler à une entrée cassée dans les logs.
            assert len(scenarios) == 1
            assert scenarios[0].id == "real_command"
            assert not any("mal formée" in r.message for r in caplog.records)

    def test_troubleshooting_entries_are_skipped_not_dropped_as_errors(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            data = [
                {
                    "id": "some_error",
                    "kind": "troubleshooting",
                    "description": "Résoudre un port déjà utilisé",
                    "tags": ["erreur", "port"],
                    "causes": ["Un autre service utilise déjà ce port."],
                    "solutions": ["Change le port ou arrête l'autre service."],
                },
            ]
            (path / "mixed.yaml").write_text(
                yaml.dump(data, allow_unicode=True), encoding="utf-8"
            )
            import logging
            with caplog.at_level(logging.WARNING):
                scenarios = YamlLoader(path).load_all()
            assert len(scenarios) == 0
            assert not any("mal formée" in r.message for r in caplog.records)

    def test_command_entry_genuinely_missing_explanation_still_warns(self, caplog):
        """A `kind: command` entry that's actually broken (missing a field
        it needs) must still surface a warning — we didn't just silence
        everything, only the legitimately different content types."""
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            data = [
                {
                    "id": "broken_command",
                    "kind": "command",
                    "description": "Une commande sans explanation",
                    "tags": ["test"],
                    "command": "echo test",
                    # "explanation" manquant volontairement
                },
            ]
            (path / "broken.yaml").write_text(
                yaml.dump(data, allow_unicode=True), encoding="utf-8"
            )
            import logging
            with caplog.at_level(logging.WARNING):
                scenarios = YamlLoader(path).load_all()
            assert len(scenarios) == 0
            assert any("mal formée" in r.message for r in caplog.records)