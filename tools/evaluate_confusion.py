"""Measure EveryCli retrieval against the maintained bilingual confusion set.

This script only measures retrieval. It never executes a suggested command and
does not claim a score until it has actually run on the current corpus.

Usage:
    python tools/evaluate_confusion.py
    python tools/evaluate_confusion.py --fail-under 80
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from everycli.core.search_engine import SearchEngine
from everycli.infra.os_resolver import OSResolver
from everycli.infra.yaml_loader import YamlLoader


DEFAULT_SET = ROOT / "eval" / "confusion_set.yaml"
DEFAULT_DATA = ROOT / "everycli" / "data" / "commands"


@dataclass(frozen=True)
class EvaluationCase:
    id: str
    locale: str
    query: str
    expected_id: str


@dataclass(frozen=True)
class EvaluationSummary:
    total: int
    top_1: int
    top_3: int
    by_locale: dict[str, tuple[int, int]]
    top_1_misses: tuple[tuple[EvaluationCase, tuple[str, ...]], ...]
    misses: tuple[tuple[EvaluationCase, tuple[str, ...]], ...]

    @property
    def top_1_percent(self) -> float:
        return 100 * self.top_1 / self.total if self.total else 0.0

    @property
    def top_3_percent(self) -> float:
        return 100 * self.top_3 / self.total if self.total else 0.0


def load_cases(path: Path) -> list[EvaluationCase]:
    raw = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(raw, dict) or not isinstance(raw.get("cases"), list):
        raise ValueError("Le fichier d'évaluation doit contenir une liste 'cases'.")
    cases = []
    for item in raw["cases"]:
        if not isinstance(item, dict):
            raise ValueError("Chaque cas d'évaluation doit être un objet YAML.")
        cases.append(EvaluationCase(
            id=str(item.get("id", "")),
            locale=str(item.get("locale", "")),
            query=str(item.get("query", "")),
            expected_id=str(item.get("expected_id", "")),
        ))
    return cases


def validate_cases(cases: Iterable[EvaluationCase], known_ids: set[str]) -> list[str]:
    """Validate benchmark data independently from the retrieval implementation."""
    errors: list[str] = []
    seen: set[str] = set()
    for case in cases:
        if not case.id:
            errors.append("Cas sans id.")
        elif case.id in seen:
            errors.append(f"Id de cas dupliqué : {case.id}")
        seen.add(case.id)
        if case.locale not in {"fr", "en"}:
            errors.append(f"{case.id}: locale doit être 'fr' ou 'en'.")
        if not case.query.strip():
            errors.append(f"{case.id}: requête vide.")
        if case.expected_id not in known_ids:
            errors.append(f"{case.id}: scénario attendu introuvable : {case.expected_id}")
    if not seen:
        errors.append("Le jeu d'évaluation ne contient aucun cas.")
    return errors


def evaluate(engine: SearchEngine, cases: Iterable[EvaluationCase]) -> EvaluationSummary:
    """Run all cases through an already-booted engine and compute retrieval ranks."""
    case_list = list(cases)
    top_1 = top_3 = 0
    locale_totals: Counter[str] = Counter()
    locale_hits: Counter[str] = Counter()
    top_1_misses: list[tuple[EvaluationCase, tuple[str, ...]]] = []
    misses: list[tuple[EvaluationCase, tuple[str, ...]]] = []
    for case in case_list:
        result_ids = tuple(result.scenario.id for result in engine.search(case.query, top_k=3))
        locale_totals[case.locale] += 1
        if result_ids[:1] == (case.expected_id,):
            top_1 += 1
            locale_hits[case.locale] += 1
        else:
            top_1_misses.append((case, result_ids))
        if case.expected_id in result_ids:
            top_3 += 1
        else:
            misses.append((case, result_ids))
    return EvaluationSummary(
        total=len(case_list), top_1=top_1, top_3=top_3,
        by_locale={locale: (locale_hits[locale], locale_totals[locale])
                   for locale in sorted(locale_totals)},
        top_1_misses=tuple(top_1_misses),
        misses=tuple(misses),
    )


def _build_engine(data_dir: Path, matcher_name: str) -> SearchEngine:
    """Build the same hybrid matcher used by the app, unless lexical is requested.

    ``lexical`` is retained for diagnosing whether a regression comes from BM25
    or from the semantic component; it is not the product default.
    """
    if matcher_name == "hybrid":
        from everycli.infra.hybrid_matcher import HybridMatcher
        matcher = HybridMatcher()
    else:
        from everycli.infra.tfidf_matcher import TFIDFMatcher
        matcher = TFIDFMatcher()
    engine = SearchEngine(YamlLoader(data_dir), matcher, OSResolver())
    engine.boot()
    return engine


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Évalue la recherche EveryCli.")
    parser.add_argument("--set", type=Path, default=DEFAULT_SET, dest="set_path")
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA, dest="data_dir")
    parser.add_argument("--matcher", choices=("hybrid", "lexical"), default="hybrid",
                        help="hybrid = moteur de l'app (défaut), lexical = diagnostic BM25.")
    parser.add_argument("--show-top1-misses", action="store_true",
                        help="Affiche les cas dont le premier résultat est incorrect.")
    parser.add_argument("--fail-under", type=float, metavar="PERCENT",
                        help="Échoue si le top-1 est sous ce pourcentage.")
    args = parser.parse_args(argv)

    try:
        cases = load_cases(args.set_path)
        scenarios = YamlLoader(args.data_dir).load_all()
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"ERROR: impossible de charger l'évaluation : {exc}")
        return 2

    errors = validate_cases(cases, {scenario.id for scenario in scenarios})
    if errors:
        print(f"ERROR: jeu d'évaluation invalide ({len(errors)} erreur(s))")
        for error in errors:
            print(f" - {error}")
        return 2

    summary = evaluate(_build_engine(args.data_dir, args.matcher), cases)
    print(f"Moteur: {args.matcher}")
    print(f"Cas: {summary.total}")
    print(f"Top-1: {summary.top_1}/{summary.total} ({summary.top_1_percent:.1f}%)")
    print(f"Top-3: {summary.top_3}/{summary.total} ({summary.top_3_percent:.1f}%)")
    for locale, (hits, total) in summary.by_locale.items():
        print(f"Top-1 {locale}: {hits}/{total} ({100 * hits / total:.1f}%)")
    if args.show_top1_misses:
        print("Misses top-1:")
        for case, result_ids in summary.top_1_misses:
            shown = ", ".join(result_ids) if result_ids else "aucun résultat"
            print(f" - {case.id}: attendu {case.expected_id}; obtenu {shown}")
    if summary.misses:
        print("Misses top-3:")
        for case, result_ids in summary.misses:
            shown = ", ".join(result_ids) if result_ids else "aucun résultat"
            print(f" - {case.id}: attendu {case.expected_id}; obtenu {shown}")
    if args.fail_under is not None and summary.top_1_percent < args.fail_under:
        print(f"ERROR: top-1 sous le seuil demandé ({args.fail_under:.1f}%).")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
