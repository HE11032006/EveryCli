import json
import sys
from types import SimpleNamespace

import pytest

from everycli.core.command_plan import LocalCommandPlanner, RiskLevel, assess_risk
from everycli.core.models import Command, Scenario, SearchResult
from everycli.infra.openai_command_planner import OpenAICommandPlanner


def _result(command: str, description: str = "Inspect a project") -> SearchResult:
    scenario = Scenario(
        id="example",
        description=description,
        tags=["linux"],
        command=Command(linux=command, windows=command),
        explanation="Example explanation.",
    )
    return SearchResult(scenario=scenario, resolved_command=command, score=0.9)


def test_read_only_command_is_low_risk():
    assert assess_risk("git status")[0] is RiskLevel.LOW


def test_destructive_command_is_high_risk():
    risk, _ = assess_risk("git reset --hard HEAD~1")
    assert risk is RiskLevel.HIGH


def test_local_plan_requires_confirmation_for_state_changes():
    plan = LocalCommandPlanner().plan(_result("docker-compose down -v", "Stop and remove a stack"))
    assert plan.risk is RiskLevel.HIGH
    assert plan.confirmation_required is True
    assert len(plan.preflight_checks) >= 3


def test_openai_planner_can_only_return_a_retrieved_command(monkeypatch):
    response = SimpleNamespace(
        output_text=json.dumps({
            "source_id": "example",
            "title": "Inspect project",
            "explanation": "Read the current state first.",
            "preflight_checks": ["Check the repository root."],
            "risk_reason": "Read-only command.",
        })
    )
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **_: response))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda: client))

    plan = OpenAICommandPlanner("gpt-5.6-terra").plan("show status", [_result("git status")])

    assert plan.command == "git status"
    assert plan.source_id == "example"
    assert plan.risk is RiskLevel.LOW


def test_openai_planner_rejects_a_command_outside_the_candidates(monkeypatch):
    response = SimpleNamespace(
        output_text=json.dumps({
            "source_id": "invented_command",
            "title": "Unsafe",
            "explanation": "Should not be accepted.",
            "preflight_checks": [],
            "risk_reason": "Unknown.",
        })
    )
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **_: response))
    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(OpenAI=lambda: client))

    with pytest.raises(ValueError, match="outside the retrieved corpus"):
        OpenAICommandPlanner("gpt-5.6-terra").plan("do something", [_result("git status")])
