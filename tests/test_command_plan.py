from everycli.core.command_plan import LocalCommandPlanner, RiskLevel, assess_risk
from everycli.core.models import Command, OS, Scenario, SearchResult


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
