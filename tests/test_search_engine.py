"""Tests for core/search_engine.py — uses fakes, zero real I/O."""

import pytest
from everycli.core.models import Command, OS, Scenario, SearchResult
from everycli.core.search_engine import SearchEngine


# ── Fakes ────────────────────────────────────────────────────────────────────

class FakeLoader:
    def __init__(self, scenarios):
        self._scenarios = scenarios

    def load_all(self):
        return self._scenarios


class FakeMatcher:
    def __init__(self, results):
        self._results = results  # list[tuple[Scenario, float]]

    def fit(self, scenarios):
        pass

    def match(self, query, top_k=3):
        return self._results[:top_k]


class FakeOSResolver:
    def __init__(self, os):
        self._os = os

    def resolve(self):
        return self._os


class FakeContextDetector:
    def __init__(self, namespaces):
        self._namespaces = namespaces

    def detect(self):
        return self._namespaces


class NullContextDetector:
    def detect(self):
        return []


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def scenario():
    return Scenario(
        id="test",
        description="Test scenario",
        tags=["test"],
        command=Command(linux="echo linux", windows="echo windows"),
        explanation="Just a test.",
    )


@pytest.fixture
def composer_scenario():
    return Scenario(
        id="composer_update",
        description="Mettre à jour les dépendances",
        tags=["update", "dépendances", "php"],
        command=Command(linux="composer update", windows="composer update"),
        explanation="Met à jour les dépendances composer.",
        namespace="composer",
    )


@pytest.fixture
def npm_scenario():
    return Scenario(
        id="npm_update",
        description="Mettre à jour les paquets",
        tags=["update", "paquets", "node"],
        command=Command(linux="npm update", windows="npm update"),
        explanation="Met à jour les paquets npm.",
        namespace="npm",
    )


@pytest.fixture
def engine(scenario):
    loader = FakeLoader([scenario])
    matcher = FakeMatcher([(scenario, 0.9)])
    resolver = FakeOSResolver(OS.LINUX)
    return SearchEngine(loader, matcher, resolver)


# Tests

class TestSearchEngine:
    def test_raises_if_search_called_before_boot(self, engine):
        with pytest.raises(RuntimeError, match="boot()"):
            engine.search("anything")

    def test_returns_results_after_boot(self, engine):
        engine.boot()
        results = engine.search("test")
        assert len(results) == 1

    def test_result_is_search_result_instance(self, engine):
        engine.boot()
        results = engine.search("test")
        assert isinstance(results[0], SearchResult)

    def test_resolves_linux_command_on_linux(self, scenario):
        engine = SearchEngine(
            FakeLoader([scenario]),
            FakeMatcher([(scenario, 0.9)]),
            FakeOSResolver(OS.LINUX),
        )
        engine.boot()
        result = engine.search("test")[0]
        assert result.resolved_command == "echo linux"

    def test_resolves_windows_command_on_windows(self, scenario):
        engine = SearchEngine(
            FakeLoader([scenario]),
            FakeMatcher([(scenario, 0.9)]),
            FakeOSResolver(OS.WINDOWS),
        )
        engine.boot()
        result = engine.search("test")[0]
        assert result.resolved_command == "echo windows"

    def test_score_is_preserved_in_result(self, engine):
        engine.boot()
        result = engine.search("test")[0]
        assert result.score == 0.9

    def test_empty_matcher_returns_empty_results(self, scenario):
        engine = SearchEngine(
            FakeLoader([scenario]),
            FakeMatcher([]),
            FakeOSResolver(OS.LINUX),
        )
        engine.boot()
        assert engine.search("anything") == []


class TestNamespaceScopeFiltering:
    """Explicit 'namespace: query' scope must filter on the reliable `namespace`
    field, not only on free-text tags — tags can be incomplete or inconsistent."""

    def test_explicit_scope_matches_namespace_even_without_matching_tag(
        self, composer_scenario, npm_scenario
    ):
        # Neither scenario has the literal word "composer" in its tags —
        # only namespace distinguishes them.
        engine = SearchEngine(
            FakeLoader([composer_scenario, npm_scenario]),
            FakeMatcher([(composer_scenario, 0.9), (npm_scenario, 0.89)]),
            FakeOSResolver(OS.LINUX),
        )
        engine.boot()
        results = engine.search("composer: mettre à jour")
        assert len(results) == 1
        assert results[0].scenario.namespace == "composer"

    def test_explicit_scope_excludes_other_namespace(
        self, composer_scenario, npm_scenario
    ):
        engine = SearchEngine(
            FakeLoader([composer_scenario, npm_scenario]),
            FakeMatcher([(composer_scenario, 0.9), (npm_scenario, 0.89)]),
            FakeOSResolver(OS.LINUX),
        )
        engine.boot()
        results = engine.search("npm: mettre à jour")
        assert all(r.scenario.namespace == "npm" for r in results)


class TestContextDetection:
    """When no explicit scope is given, an injected ContextDetector (e.g. detecting
    composer.json in the cwd) auto-filters results to the relevant namespace(s)."""

    def test_no_explicit_scope_and_no_context_behaves_like_before(
        self, composer_scenario, npm_scenario
    ):
        engine = SearchEngine(
            FakeLoader([composer_scenario, npm_scenario]),
            FakeMatcher([(npm_scenario, 0.9), (composer_scenario, 0.89)]),
            FakeOSResolver(OS.LINUX),
            context_detector=NullContextDetector(),
        )
        engine.boot()
        results = engine.search("mettre à jour")
        assert [r.scenario.namespace for r in results] == ["npm", "composer"]

    def test_detected_context_filters_to_matching_namespace(
        self, composer_scenario, npm_scenario
    ):
        # Matcher ranks npm first, but the detected project context is composer
        # (e.g. a composer.json was found in the cwd) — composer should win.
        engine = SearchEngine(
            FakeLoader([composer_scenario, npm_scenario]),
            FakeMatcher([(npm_scenario, 0.9), (composer_scenario, 0.89)]),
            FakeOSResolver(OS.LINUX),
            context_detector=FakeContextDetector(["composer"]),
        )
        engine.boot()
        results = engine.search("mettre à jour")
        assert len(results) == 1
        assert results[0].scenario.namespace == "composer"

    def test_explicit_scope_takes_priority_over_detected_context(
        self, composer_scenario, npm_scenario
    ):
        engine = SearchEngine(
            FakeLoader([composer_scenario, npm_scenario]),
            FakeMatcher([(npm_scenario, 0.9), (composer_scenario, 0.89)]),
            FakeOSResolver(OS.LINUX),
            context_detector=FakeContextDetector(["composer"]),
        )
        engine.boot()
        results = engine.search("npm: mettre à jour")
        assert len(results) == 1
        assert results[0].scenario.namespace == "npm"

    def test_context_detector_is_optional_for_backward_compat(self, scenario):
        # No context_detector argument at all — must still work (existing callers).
        engine = SearchEngine(
            FakeLoader([scenario]),
            FakeMatcher([(scenario, 0.9)]),
            FakeOSResolver(OS.LINUX),
        )
        engine.boot()
        assert len(engine.search("test")) == 1

    def test_context_with_no_matching_namespace_falls_back_unfiltered(
        self, composer_scenario, npm_scenario
    ):
        # Detected namespace has no scenarios at all — don't return empty-handed.
        engine = SearchEngine(
            FakeLoader([composer_scenario, npm_scenario]),
            FakeMatcher([(npm_scenario, 0.9), (composer_scenario, 0.89)]),
            FakeOSResolver(OS.LINUX),
            context_detector=FakeContextDetector(["docker"]),
        )
        engine.boot()
        results = engine.search("mettre à jour")
        assert len(results) == 2

    def test_context_override_is_used_instead_of_injected_detector(
        self, composer_scenario, npm_scenario
    ):
        # Simulates the daemon: it has no reliable ContextDetector of its own
        # (its cwd isn't the user's), so the caller (daemon_server) passes the
        # context detected client-side directly via context_override.
        engine = SearchEngine(
            FakeLoader([composer_scenario, npm_scenario]),
            FakeMatcher([(npm_scenario, 0.9), (composer_scenario, 0.89)]),
            FakeOSResolver(OS.LINUX),
            context_detector=None,
        )
        engine.boot()
        results = engine.search("mettre à jour", context_override=["composer"])
        assert len(results) == 1
        assert results[0].scenario.namespace == "composer"

    def test_context_override_empty_list_means_no_context_detected(
        self, composer_scenario, npm_scenario
    ):
        # An explicit empty list (client checked, found nothing) must behave
        # like "no context", not be confused with "no override given" (None).
        engine = SearchEngine(
            FakeLoader([composer_scenario, npm_scenario]),
            FakeMatcher([(npm_scenario, 0.9), (composer_scenario, 0.89)]),
            FakeOSResolver(OS.LINUX),
        )
        engine.boot()
        results = engine.search("mettre à jour", context_override=[])
        assert [r.scenario.namespace for r in results] == ["npm", "composer"]

    def test_explicit_scope_takes_priority_over_context_override(
        self, composer_scenario, npm_scenario
    ):
        engine = SearchEngine(
            FakeLoader([composer_scenario, npm_scenario]),
            FakeMatcher([(npm_scenario, 0.9), (composer_scenario, 0.89)]),
            FakeOSResolver(OS.LINUX),
        )
        engine.boot()
        results = engine.search("npm: mettre à jour", context_override=["composer"])
        assert len(results) == 1
        assert results[0].scenario.namespace == "npm"
    def test_natural_namespace_beats_context_and_stays_strict(self):
        python = Scenario(
            "python_venv", "Create a virtual environment", ["python"],
            Command("python -m venv .venv", "python -m venv .venv"), "", namespace="python",
        )
        docker = Scenario(
            "docker_build", "Build a Docker image", ["docker"],
            Command("docker build .", "docker build ."), "", namespace="docker",
        )
        compose = Scenario(
            "compose_build", "Build Compose services", ["docker", "compose"],
            Command("docker compose build", "docker compose build"), "", namespace="docker_compose",
        )
        engine = SearchEngine(
            FakeLoader([python, docker, compose]),
            FakeMatcher([(python, 0.9), (docker, 0.8), (compose, 0.7)]),
            FakeOSResolver(OS.LINUX),
            context_detector=FakeContextDetector(["python"]),
        )
        engine.boot()

        assert [r.scenario.namespace for r in engine.search("docker build an image")] == ["docker"]
        assert [r.scenario.namespace for r in engine.search("docker-compose build services")] == ["docker_compose"]
        assert [r.scenario.namespace for r in engine.search("docker: build")] == ["docker"]

    def test_aliases_override_project_context(self):
        python = Scenario(
            "pip_install", "Install a Python package", ["python", "pip"],
            Command("python -m pip install package", "python -m pip install package"), "", namespace="python",
        )
        linux = Scenario(
            "restart_service", "Restart a service", ["linux", "systemd"],
            Command("systemctl restart service", "systemctl restart service"), "", namespace="linux",
        )
        engine = SearchEngine(
            FakeLoader([python, linux]),
            FakeMatcher([(linux, 0.9), (python, 0.8)]),
            FakeOSResolver(OS.LINUX),
            context_detector=FakeContextDetector(["linux"]),
        )
        engine.boot()

        assert [r.scenario.namespace for r in engine.search("pip install requests")] == ["python"]
        assert [r.scenario.namespace for r in engine.search("restart a systemctl service")] == ["linux"]

    def test_context_does_not_hide_a_clearly_better_other_ecosystem(self):
        python = Scenario(
            "python_venv", "Create a virtual environment", ["python"],
            Command("python -m venv .venv", "python -m venv .venv"), "", namespace="python",
        )
        linux = Scenario(
            "list_processes", "List running processes", ["linux", "processes"],
            Command("ps aux", "Get-Process"), "", namespace="linux",
        )
        engine = SearchEngine(
            FakeLoader([python, linux]),
            FakeMatcher([(linux, 0.95), (python, 0.2)]),
            FakeOSResolver(OS.LINUX),
            context_detector=FakeContextDetector(["python"]),
        )
        engine.boot()

        results = engine.search("list all running processes")
        assert [r.scenario.namespace for r in results] == ["linux", "python"]
