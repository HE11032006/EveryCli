"""Tests for tools/validate_corpus.py — the strict corpus validator.

Unlike YamlLoader (tolerant, skips bad entries so the running app never
crashes), this validator is meant to be run explicitly (locally, in CI, or
after a Codex-generated batch) and must FAIL LOUDLY, reporting every problem
in the corpus at once — not just the first one.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from tools.validate_corpus import validate_corpus, ValidationError


def _write(tmpdir: Path, filename: str, entries: list[dict]) -> None:
    (tmpdir / filename).write_text(yaml.dump(entries, allow_unicode=True), encoding="utf-8")


class TestValidateCorpus:
    def test_valid_command_entry_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "git.yaml", [{
                "id": "git_status",
                "kind": "command",
                "description": "Voir l'état du dépôt",
                "tags": ["git", "status"],
                "commands": {"linux": "git status", "windows": "git status"},
                "explanation": "Affiche l'état du dépôt.",
            }])
            errors = validate_corpus(path)
            assert errors == []

    def test_missing_explanation_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "git.yaml", [{
                "id": "git_broken",
                "kind": "command",
                "description": "Cassé",
                "tags": ["git"],
                "commands": {"linux": "git status"},
                # explanation manquant
            }])
            errors = validate_corpus(path)
            assert len(errors) == 1
            assert "git_broken" in errors[0]
            assert "explanation" in errors[0]

    def test_reports_all_errors_not_just_the_first(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "git.yaml", [
                {"id": "broken_1", "kind": "command", "description": "x", "tags": []},
                {"id": "broken_2", "kind": "command", "description": "y", "tags": []},
            ])
            errors = validate_corpus(path)
            # Chaque entrée a plusieurs problèmes à la fois (tags vide,
            # explanation manquante, command manquante) — on vérifie que les
            # DEUX entrées cassées remontent, pas seulement la première.
            assert any("broken_1" in e for e in errors)
            assert any("broken_2" in e for e in errors)
            assert len(errors) > 2

    def test_tip_requires_content_field(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "docker_compose.yaml", [{
                "id": "some_tip",
                "kind": "tip",
                "description": "Une astuce",
                "tags": ["astuce"],
                # content manquant
            }])
            errors = validate_corpus(path)
            assert len(errors) == 1
            assert "content" in errors[0]

    def test_valid_tip_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "docker_compose.yaml", [{
                "id": "some_tip",
                "kind": "tip",
                "description": "Une astuce",
                "tags": ["astuce"],
                "content": "Fais ceci.",
            }])
            assert validate_corpus(path) == []

    def test_troubleshooting_requires_causes_and_solutions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "docker_compose.yaml", [{
                "id": "some_error",
                "kind": "troubleshooting",
                "description": "Erreur",
                "tags": ["erreur"],
                "causes": ["une cause"],
                # solutions manquant
            }])
            errors = validate_corpus(path)
            assert len(errors) == 1
            assert "solutions" in errors[0]

    def test_reference_requires_content_field(self):
        """kind=reference : documentation de syntaxe (ex: la clé `version:`
        d'un docker-compose.yml) — pas une commande, pas un tip, pas une
        erreur, mais un 4e type légitime rencontré dans le vrai corpus."""
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "docker_compose.yaml", [{
                "id": "docker_compose_version_key",
                "kind": "reference",
                "description": "Spécifier la version du schéma",
                "tags": ["docker", "compose", "yaml"],
                # content manquant
            }])
            errors = validate_corpus(path)
            assert len(errors) == 1
            assert "content" in errors[0]

    def test_valid_reference_passes(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "docker_compose.yaml", [{
                "id": "docker_compose_version_key",
                "kind": "reference",
                "description": "Spécifier la version du schéma",
                "tags": ["docker", "compose", "yaml"],
                "content": 'version: "3.8"',
            }])
            assert validate_corpus(path) == []

    def test_unknown_kind_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "git.yaml", [{
                "id": "weird",
                "kind": "mystery",
                "description": "x",
                "tags": [],
            }])
            errors = validate_corpus(path)
            assert len(errors) == 1
            assert "kind" in errors[0]

    def test_duplicate_id_across_files_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            entry = {
                "id": "dup_id",
                "kind": "command",
                "description": "x",
                "tags": [],
                "commands": {"linux": "echo x"},
                "explanation": "x",
            }
            _write(path, "git.yaml", [entry])
            _write(path, "docker.yaml", [entry])
            errors = validate_corpus(path)
            assert any("dup_id" in e and "dupliqué" in e for e in errors)

    def test_empty_tags_list_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "git.yaml", [{
                "id": "no_tags",
                "kind": "command",
                "description": "x",
                "tags": [],
                "commands": {"linux": "echo x"},
                "explanation": "x",
            }])
            errors = validate_corpus(path)
            assert len(errors) == 1
            assert "tags" in errors[0]

    def test_command_missing_both_command_and_commands_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "git.yaml", [{
                "id": "no_cmd",
                "kind": "command",
                "description": "x",
                "tags": ["x"],
                "explanation": "x",
                # ni "command" ni "commands"
            }])
            errors = validate_corpus(path)
            assert len(errors) == 1
            assert "command" in errors[0]

    def test_valid_full_corpus_returns_no_errors(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)
            _write(path, "git.yaml", [
                {
                    "id": "git_status",
                    "kind": "command",
                    "description": "Voir l'état",
                    "tags": ["git", "status"],
                    "commands": {"linux": "git status", "windows": "git status"},
                    "explanation": "Affiche l'état du dépôt.",
                },
            ])
            _write(path, "docker_compose.yaml", [
                {
                    "id": "some_tip",
                    "kind": "tip",
                    "description": "Astuce",
                    "tags": ["astuce"],
                    "content": "Fais ceci.",
                },
            ])
            assert validate_corpus(path) == []