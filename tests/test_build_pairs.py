"""Tests for training/build_pairs.py — training pair construction for the
semantic model fine-tuning script (does not touch the real corpus or run
any training; pure data-shaping logic)."""

import json

from everycli.core.models import Command, Scenario
from training.build_pairs import (
    build_pairs,
    load_expected_ids,
    scenario_pairs,
    write_pairs_jsonl,
)


def _scenario(id_, description="Build an image", tags=None, explanation="Explains it"):
    return Scenario(
        id=id_,
        description=description,
        tags=tags or ["docker", "build"],
        command=Command(linux="docker build .", windows="docker build ."),
        explanation=explanation,
    )


def test_scenario_pairs_includes_description_command_and_tags():
    scenario = _scenario("docker_build_image")
    pairs = scenario_pairs(scenario)

    assert ("Build an image", "docker build .") in pairs
    assert ("Build an image", "Explains it") in pairs
    assert ("docker build", "Build an image") in pairs


def test_build_pairs_excludes_scenarios_used_in_the_eval_set():
    kept = _scenario("docker_build_image")
    excluded = _scenario("git_stash_changes", description="Stash your work")

    pairs = build_pairs([kept, excluded], excluded_ids={"git_stash_changes"})

    assert any("Build an image" in pair for pair in pairs)
    assert not any("Stash your work" in pair for pair in pairs)


def test_load_expected_ids_reads_the_confusion_set(tmp_path):
    confusion_set = tmp_path / "confusion_set.yaml"
    confusion_set.write_text(
        """
version: 1
cases:
  - {id: a, locale: fr, query: "q1", expected_id: git_stash_changes}
  - {id: b, locale: en, query: "q2", expected_id: docker_build_image}
""",
        encoding="utf-8",
    )

    assert load_expected_ids(confusion_set) == {"git_stash_changes", "docker_build_image"}


def test_write_pairs_jsonl_writes_one_json_object_per_line(tmp_path):
    output_path = tmp_path / "pairs.jsonl"
    write_pairs_jsonl([("a", "b"), ("c", "d")], output_path)

    lines = output_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 2
    assert json.loads(lines[0]) == {"text_a": "a", "text_b": "b"}
    assert json.loads(lines[1]) == {"text_a": "c", "text_b": "d"}
