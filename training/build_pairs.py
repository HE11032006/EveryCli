"""Build positive training pairs for fine-tuning the semantic model.

Reuses the existing corpus loader (everycli.infra.yaml_loader.YamlLoader) so
this never reimplements YAML parsing. Scenarios used by eval/confusion_set.yaml
are excluded on purpose: that file is the non-regression gate
(tools/evaluate_confusion.py) for any fine-tuned model, so it must never also
be training data.

Usage:
    python training/build_pairs.py
    python training/build_pairs.py --output training/pairs.jsonl
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from everycli.core.models import Scenario
from everycli.infra.yaml_loader import YamlLoader

DEFAULT_DATA_DIR = ROOT / "everycli" / "data" / "commands"
DEFAULT_CONFUSION_SET = ROOT / "eval" / "confusion_set.yaml"
DEFAULT_OUTPUT = Path(__file__).resolve().parent / "pairs.jsonl"


def load_expected_ids(confusion_set_path: Path) -> set[str]:
    """IDs already used as ground truth in the eval gate — never train on these."""
    data = yaml.safe_load(confusion_set_path.read_text(encoding="utf-8")) or {}
    return {case["expected_id"] for case in data.get("cases", [])}


# def scenario_pairs(scenario: Scenario) -> list[tuple[str, str]]:
#     """Positive pairs for one scenario: different natural views of the same
#     intent, so MultipleNegativesRankingLoss can pull them together. Mirrors
#     the tags/command weighting already used for retrieval documents in
#     everycli/infra/semantic_matcher.py::_scenario_to_document."""
#     pairs = []
#     description = scenario.description.strip()
#     if not description:
#         return pairs

#     command = scenario.command.linux.strip()
#     if command:
#         pairs.append((description, command))

#     explanation = scenario.explanation.strip()
#     if explanation and explanation != description:
#         pairs.append((description, explanation))

#     tags_phrase = " ".join(scenario.tags).strip()
#     if tags_phrase:
#         pairs.append((tags_phrase, description))

#     return pairs

def scenario_pairs(scenario: Scenario) -> list[tuple[str, str]]:
    """Positive pairs for one scenario."""
    pairs = []
    description = scenario.description.strip()
    if not description:
        return pairs  # ← Retourne une liste vide, pas None

    command = scenario.command.linux.strip()
    if command:
        pairs.append((description, command))

    explanation = scenario.explanation.strip()
    if explanation and explanation != description:
        pairs.append((description, explanation))

    tags_phrase = " ".join(scenario.tags).strip()
    if tags_phrase:
        pairs.append((description + " " + tags_phrase, description))
        pairs.append((tags_phrase, command))
        pairs.append((tags_phrase, tags_phrase))

    return pairs

def build_pairs(scenarios: list[Scenario], excluded_ids: set[str]) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for scenario in scenarios:
        if scenario.id in excluded_ids:
            continue
        pairs.extend(scenario_pairs(scenario))
    return pairs


def write_pairs_jsonl(pairs: list[tuple[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as handle:
        for text_a, text_b in pairs:
            handle.write(json.dumps({"text_a": text_a, "text_b": text_b}, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--confusion-set", type=Path, default=DEFAULT_CONFUSION_SET)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    scenarios = YamlLoader(args.data).load_all()
    excluded_ids = load_expected_ids(args.confusion_set)
    pairs = build_pairs(scenarios, excluded_ids)
    write_pairs_jsonl(pairs, args.output)

    print(f"{len(pairs)} pairs written to {args.output} ({len(excluded_ids)} scenarios excluded)")


if __name__ == "__main__":
    main()
