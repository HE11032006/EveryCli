"""Tests for infra/yaml_writer.py"""

import pytest
import tempfile
import yaml
from pathlib import Path

from everycli.core.models import Command, ErrorHint, Scenario
from everycli.infra.yaml_writer import YamlWriter


@pytest.fixture
def scenario():
    return Scenario(
        id="git_test",
        description="Tester quelque chose",
        tags=["git", "test"],
        command=Command(linux="git test", windows="git test"),
        explanation="Juste un test.",
        warning="Attention test.",
        error_hints=[
            ErrorHint(
                trigger="fatal: test",
                cause="Cause de test",
                fix="Fix de test",
            )
        ],
    )


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class TestYamlWriter:
    def test_creates_file_if_not_exists(self, tmp_dir, scenario):
        writer = YamlWriter(tmp_dir)
        writer.write(scenario, "git")
        assert (tmp_dir / "git.yaml").exists()

    def test_written_scenario_has_correct_id(self, tmp_dir, scenario):
        YamlWriter(tmp_dir).write(scenario, "git")
        data = yaml.safe_load((tmp_dir / "git.yaml").read_text())
        assert data[0]["id"] == "git_test"

    def test_written_scenario_has_warning(self, tmp_dir, scenario):
        YamlWriter(tmp_dir).write(scenario, "git")
        data = yaml.safe_load((tmp_dir / "git.yaml").read_text())
        assert data[0]["warning"] == "Attention test."

    def test_written_scenario_has_error_hints(self, tmp_dir, scenario):
        YamlWriter(tmp_dir).write(scenario, "git")
        data = yaml.safe_load((tmp_dir / "git.yaml").read_text())
        assert len(data[0]["errors"]) == 1
        assert data[0]["errors"][0]["trigger"] == "fatal: test"

    def test_appends_to_existing_file(self, tmp_dir, scenario):
        writer = YamlWriter(tmp_dir)
        writer.write(scenario, "git")
        writer.write(scenario, "git")
        data = yaml.safe_load((tmp_dir / "git.yaml").read_text())
        assert len(data) == 2

    def test_no_warning_key_when_empty(self, tmp_dir):
        scenario = Scenario(
            id="test",
            description="test",
            tags=["test"],
            command=Command(linux="echo", windows="echo"),
            explanation="test",
        )
        YamlWriter(tmp_dir).write(scenario, "test")
        data = yaml.safe_load((tmp_dir / "test.yaml").read_text())
        assert "warning" not in data[0]