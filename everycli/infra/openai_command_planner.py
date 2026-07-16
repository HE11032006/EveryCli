"""GPT-5.6 command-plan refinement with strict corpus grounding.

The model receives retrieved candidates, but is never allowed to invent a
shell command.  A deterministic local risk classifier remains authoritative.
"""

from __future__ import annotations

import json
import os

from everycli.core.command_plan import CommandPlan, LocalCommandPlanner, RiskLevel, assess_risk
from everycli.core.models import SearchResult


SYSTEM_PROMPT = """You are EveryCli Sentinel, a Linux command safety planner.
Choose exactly one of the provided candidates. Never invent, modify, combine,
or execute shell commands. Explain the selected candidate in the user's
language, identify assumptions, and give concise preflight checks. Return only
valid JSON with: source_id, title, explanation, preflight_checks (array of
strings), and risk_reason. If the request is ambiguous, say what must be
confirmed in preflight_checks. Do not claim that a command is safe."""


class OpenAICommandPlanner:
    """Optional GPT-5.6 planner; falls back safely if the API is unavailable."""

    name = "gpt-5.6-terra"

    def __init__(self, model: str | None = None):
        self._model = model or os.environ.get("EVERYCLI_OPENAI_MODEL", self.name)

    @classmethod
    def available(cls) -> bool:
        return bool(os.environ.get("OPENAI_API_KEY"))

    def plan(self, query: str, candidates: list[SearchResult]) -> CommandPlan:
        if not candidates:
            raise ValueError("At least one retrieved command is required to build a plan.")

        # Import only when this optional capability is actually requested.
        from openai import OpenAI

        candidate_payload = [
            {
                "id": candidate.scenario.id,
                "description": candidate.scenario.description,
                "command": candidate.resolved_command,
                "explanation": candidate.scenario.explanation,
                "warning": candidate.scenario.warning,
            }
            for candidate in candidates
        ]
        response = OpenAI().responses.create(
            model=self._model,
            instructions=SYSTEM_PROMPT,
            input=json.dumps({"user_request": query, "candidates": candidate_payload}, ensure_ascii=False),
        )
        payload = json.loads(response.output_text)
        by_id = {candidate.scenario.id: candidate for candidate in candidates}
        chosen = by_id.get(payload.get("source_id"))
        if chosen is None:
            raise ValueError("The AI response selected a command outside the retrieved corpus.")

        # The command and risk are always taken from deterministic, local data.
        risk, fallback_reason = assess_risk(chosen.resolved_command, chosen.scenario.description)
        checks = payload.get("preflight_checks", [])
        if not isinstance(checks, list) or not all(isinstance(item, str) for item in checks):
            checks = []
        if not checks:
            checks = LocalCommandPlanner().plan(chosen).preflight_checks

        return CommandPlan(
            source_id=chosen.scenario.id,
            command=chosen.resolved_command,
            title=str(payload.get("title") or chosen.scenario.description),
            explanation=str(payload.get("explanation") or chosen.scenario.explanation),
            risk=risk,
            risk_reason=str(payload.get("risk_reason") or fallback_reason),
            preflight_checks=checks,
            confirmation_required=risk is not RiskLevel.LOW,
            planner=self._model,
        )
