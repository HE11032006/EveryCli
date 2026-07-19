from everycli.core.models import Command, OS, Scenario
from everycli.core.search_engine import SearchEngine
from tools.evaluate_confusion import (
    DEFAULT_DATA, DEFAULT_SET, EvaluationCase, evaluate, load_cases, validate_cases,
)


class FakeLoader:
    def __init__(self, scenarios): self.scenarios = scenarios
    def load_all(self): return self.scenarios


class FakeMatcher:
    def __init__(self, results): self.results = results
    def fit(self, scenarios): pass
    def match(self, query, top_k=3): return self.results[:top_k]


class FakeResolver:
    def resolve(self): return OS.LINUX


def _scenario(identifier):
    return Scenario(identifier, identifier, ["test"], Command("echo test", "echo test"), "test")


def test_confusion_set_references_real_corpus_commands():
    from everycli.infra.yaml_loader import YamlLoader
    cases = load_cases(DEFAULT_SET)
    known_ids = {scenario.id for scenario in YamlLoader(DEFAULT_DATA).load_all()}
    assert len(cases) >= 50
    assert validate_cases(cases, known_ids) == []


def test_validate_cases_reports_duplicate_and_unknown_scenario():
    cases = [
        EvaluationCase("same", "fr", "une recherche", "known"),
        EvaluationCase("same", "en", "another search", "missing"),
    ]
    errors = validate_cases(cases, {"known"})
    assert any("dupliqué" in error for error in errors)
    assert any("missing" in error for error in errors)


def test_evaluate_aggregates_top_one_top_three_and_locales():
    expected, other = _scenario("expected"), _scenario("other")
    engine = SearchEngine(
        FakeLoader([expected, other]),
        FakeMatcher([(other, 0.9), (expected, 0.8)]),
        FakeResolver(),
    )
    engine.boot()
    summary = evaluate(engine, [
        EvaluationCase("one", "fr", "query", "expected"),
        EvaluationCase("two", "en", "query", "other"),
    ])
    assert summary.top_1 == 1
    assert summary.top_3 == 2
    assert summary.by_locale == {"en": (1, 1), "fr": (0, 1)}
    assert summary.top_1_misses[0][0].id == "one"
    assert summary.misses == ()
