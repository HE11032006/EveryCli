"""Safe, explainable command plans.

EveryCli retrieves the command.  This module turns that retrieval into a plan
the user can inspect *before* anything is copied or executed.  It deliberately
contains no shell execution code.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from everycli.core.models import SearchResult


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


@dataclass(frozen=True)
class CommandPlan:
    """A reviewable recommendation for one CLI action."""

    source_id: str
    command: str
    title: str
    explanation: str
    risk: RiskLevel
    risk_reason: str
    preflight_checks: list[str]
    confirmation_required: bool
    planner: str


_HIGH_RISK_PATTERNS = (
    "rm ", "rmdir ", "mkfs", " dd ", "shutdown", "reboot", "poweroff",
    "docker system prune", "docker-compose down -v", "git reset --hard",
    "git clean -f", "chmod 777",
)
_MEDIUM_RISK_PATTERNS = (
    "delete", "remove", "prune", "stop", "down", "kill", "push", "commit",
    "install", "upgrade", "update", "chmod", "chown",
)


def assess_risk(command: str, description: str = "") -> tuple[RiskLevel, str]:
    """Classify a command locally and deterministically.

    This remains the final safety gate even when an AI planner is enabled.
    """
    text = f"{command} {description}".lower()
    if any(pattern in text for pattern in _HIGH_RISK_PATTERNS):
        return RiskLevel.HIGH, "This action can delete data, alter system state, or be hard to undo."
    if any(pattern in text for pattern in _MEDIUM_RISK_PATTERNS):
        return RiskLevel.MEDIUM, "This action changes project, package, or service state."
    return RiskLevel.LOW, "This action appears read-only or reversible."


class LocalCommandPlanner:
    """Safe fallback used without an OpenAI API key or network access."""

    name = "local-safety-rules"

    def plan(self, result: SearchResult) -> CommandPlan:
        risk, reason = assess_risk(result.resolved_command, result.scenario.description)
        checks = ["Read the command and replace every placeholder before running it."]
        if risk is RiskLevel.MEDIUM:
            checks.append("Confirm the target project, service, or package is the intended one.")
        if risk is RiskLevel.HIGH:
            checks.extend([
                "Verify the target path or resource; do not run it from an uncertain directory.",
                "Make a backup or use a dry-run/preview command when one is available.",
            ])

        return CommandPlan(
            source_id=result.scenario.id,
            command=result.resolved_command,
            title=result.scenario.description,
            explanation=result.scenario.explanation,
            risk=risk,
            risk_reason=reason,
            preflight_checks=checks,
            confirmation_required=risk is not RiskLevel.LOW,
            planner=self.name,
        )
