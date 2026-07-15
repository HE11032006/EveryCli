"""Tests for infra/context_detector.py — real filesystem, isolated in tmp dirs."""

import tempfile
from pathlib import Path

from everycli.infra.context_detector import ProjectContextDetector


class TestProjectContextDetector:
    def test_empty_directory_detects_nothing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            detector = ProjectContextDetector(cwd=Path(tmpdir))
            assert detector.detect() == []

    def test_composer_json_detects_composer(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "composer.json").write_text("{}", encoding="utf-8")
            detector = ProjectContextDetector(cwd=path)
            assert detector.detect() == ["composer"]

    def test_package_json_detects_npm(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "package.json").write_text("{}", encoding="utf-8")
            detector = ProjectContextDetector(cwd=path)
            assert detector.detect() == ["npm"]

    def test_git_directory_detects_git(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / ".git").mkdir()
            detector = ProjectContextDetector(cwd=path)
            assert detector.detect() == ["git"]

    def test_dockerfile_detects_docker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "Dockerfile").write_text("FROM python", encoding="utf-8")
            detector = ProjectContextDetector(cwd=path)
            assert detector.detect() == ["docker"]

    def test_docker_compose_detects_both_docker_compose_and_docker(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "docker-compose.yml").write_text("services: {}", encoding="utf-8")
            detector = ProjectContextDetector(cwd=path)
            assert detector.detect() == ["docker_compose", "docker"]

    def test_multiple_markers_combine_without_duplicates(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir)
            (path / "composer.json").write_text("{}", encoding="utf-8")
            (path / ".git").mkdir()
            (path / "Dockerfile").write_text("FROM php", encoding="utf-8")
            detector = ProjectContextDetector(cwd=path)
            detected = detector.detect()
            assert set(detected) == {"composer", "git", "docker"}
            assert len(detected) == len(set(detected))  # no duplicates

    def test_defaults_to_real_cwd_when_none_given(self):
        # Just verify it doesn't crash and returns a list when cwd is omitted.
        detector = ProjectContextDetector()
        assert isinstance(detector.detect(), list)