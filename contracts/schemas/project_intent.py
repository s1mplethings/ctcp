from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from contracts.validation import optional_string, optional_string_list, require_dict


def _fallback_goal_summary(user_goal: str, payload: dict[str, Any]) -> str:
    text = str(payload.get("goal_summary", "") or user_goal or "").strip()
    return text or "deliver a runnable MVP project"


@dataclass(frozen=True)
class ProjectIntent:
    goal_summary: str
    target_user: str
    problem_to_solve: str
    mvp_scope: list[str]
    required_inputs: list[str]
    required_outputs: list[str]
    hard_constraints: list[str]
    assumptions: list[str]
    open_questions: list[str]
    acceptance_criteria: list[str]

    @classmethod
    def from_payload(cls, payload: dict[str, Any], *, user_goal: str = "") -> "ProjectIntent":
        doc = require_dict(payload, field="project_intent")
        return cls(
            goal_summary=_fallback_goal_summary(user_goal, doc),
            target_user=optional_string(doc, "target_user") or "primary operator of the generated MVP",
            problem_to_solve=optional_string(doc, "problem_to_solve") or "translate the user's vague goal into a runnable MVP",
            mvp_scope=optional_string_list(doc, "mvp_scope") or ["deliver the smallest runnable MVP loop"],
            required_inputs=optional_string_list(doc, "required_inputs"),
            required_outputs=optional_string_list(doc, "required_outputs") or ["a runnable project package"],
            hard_constraints=optional_string_list(doc, "hard_constraints"),
            assumptions=optional_string_list(doc, "assumptions") or ["missing non-blocking details may use pragmatic defaults"],
            open_questions=optional_string_list(doc, "open_questions"),
            acceptance_criteria=optional_string_list(doc, "acceptance_criteria")
            or ["the generated project can be started from the README and complete one core user flow"],
        )

    @classmethod
    def minimal_from_goal(cls, user_goal: str, constraints: dict[str, Any] | None = None) -> "ProjectIntent":
        rows: list[str] = []
        if isinstance(constraints, dict):
            for key, value in constraints.items():
                text = str(value or "").strip()
                if text:
                    rows.append(f"{key}={text}")
                elif isinstance(value, bool) and value:
                    rows.append(key)
        return cls(
            goal_summary=str(user_goal or "").strip() or "deliver a runnable MVP project",
            target_user="requesting user or project operator",
            problem_to_solve="the user has a broad request that still needs to be turned into a runnable MVP",
            mvp_scope=["deliver a first runnable slice instead of only planning artifacts"],
            required_inputs=[],
            required_outputs=["a runnable project package", "startup instructions", "one validated core user flow"],
            hard_constraints=rows,
            assumptions=["frontend or caller did not provide a richer ProjectIntent, so backend is using a compatibility fallback"],
            open_questions=[],
            acceptance_criteria=["the MVP can be started and demonstrate one core user flow"],
        )

    def to_payload(self) -> dict[str, Any]:
        return {
            "goal_summary": self.goal_summary,
            "target_user": self.target_user,
            "problem_to_solve": self.problem_to_solve,
            "mvp_scope": list(self.mvp_scope),
            "required_inputs": list(self.required_inputs),
            "required_outputs": list(self.required_outputs),
            "hard_constraints": list(self.hard_constraints),
            "assumptions": list(self.assumptions),
            "open_questions": list(self.open_questions),
            "acceptance_criteria": list(self.acceptance_criteria),
        }

    def to_text_brief(self) -> str:
        scope = "；".join(self.mvp_scope[:3])
        return f"{self.goal_summary} | 用户={self.target_user} | 范围={scope}"
