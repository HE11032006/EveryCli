from everycli.core.models import Command, Scenario
from everycli.infra.hybrid_matcher import HybridMatcher


def _scenario(identifier: str) -> Scenario:
    return Scenario(
        id=identifier,
        description=identifier,
        tags=["test"],
        command=Command(linux="echo test", windows="echo test"),
        explanation="test",
    )


def test_high_lexical_score_with_small_gap_uses_semantic_reranking():
    matcher = HybridMatcher(fast_threshold=0.55, ambiguity_margin=0.12)
    first, second = _scenario("first"), _scenario("second")
    matcher._fitted = True
    matcher._scenarios = [first, second]

    class Lexical:
        def match(self, query, top_k):
            return [(first, 0.91), (second, 0.86)]

    class Semantic:
        def match(self, query, top_k):
            return [(second, 1.0), (first, 0.1)]

    matcher._tfidf = Lexical()
    matcher._semantic = Semantic()
    results = matcher.match("ambiguous request")

    assert matcher.used_semantic is True
    assert results[0][0].id == "second"


def test_large_lexical_gap_keeps_fast_path():
    matcher = HybridMatcher(fast_threshold=0.55, ambiguity_margin=0.12)
    first, second = _scenario("first"), _scenario("second")
    matcher._fitted = True
    matcher._scenarios = [first, second]

    class Lexical:
        def match(self, query, top_k):
            return [(first, 0.91), (second, 0.50)]

    class Semantic:
        def match(self, query, top_k):
            raise AssertionError("semantic matcher should not be called")

    matcher._tfidf = Lexical()
    matcher._semantic = Semantic()
    results = matcher.match("clear request")

    assert matcher.used_semantic is False
    assert [scenario.id for scenario, _ in results] == ["first", "second"]
