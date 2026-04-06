from __future__ import annotations

from typing import Any

from apps.project_backend.application.delivery_evidence import fallback_delivery_evidence
from apps.project_backend.config import BackendConfig
from apps.project_backend.domain.job import JobRecord
from apps.project_backend.orchestrator.event_bus import EventBus
from apps.project_backend.orchestrator.failure_handler import failure_event
from apps.project_backend.orchestrator.job_runner import BridgeAdapter, JobRunner
from apps.project_backend.orchestrator.phase_machine import phase_from_bridge_status
from apps.project_backend.orchestrator.question_bus import QuestionBus
from apps.project_backend.storage.job_store import JobStore
from contracts.enums import JobPhase
from contracts.schemas.project_intent import ProjectIntent
from contracts.schemas.event_question import QuestionEvent
from contracts.schemas.event_result import ResultEvent
from contracts.schemas.event_status import StatusEvent
from contracts.schemas.job_answer import JobAnswerRequest
from contracts.schemas.job_create import JobCreateRequest
from shared.ids import new_event_id


def _should_emit_backend_test_default_output(constraints: dict[str, Any]) -> bool:
    value = constraints.get("backend_test_default_output", False)
    if isinstance(value, bool):
        return value
    text = str(value or "").strip().lower()
    return text in {"1", "true", "yes", "on"}


def _build_project_spec(intent: ProjectIntent, constraints: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "ctcp-project-spec-v1",
        "goal_summary": intent.goal_summary,
        "target_user": intent.target_user,
        "problem_to_solve": intent.problem_to_solve,
        "mvp_scope": list(intent.mvp_scope),
        "required_inputs": list(intent.required_inputs),
        "required_outputs": list(intent.required_outputs),
        "hard_constraints": list(intent.hard_constraints),
        "assumptions": list(intent.assumptions),
        "open_questions": list(intent.open_questions),
        "acceptance_criteria": list(intent.acceptance_criteria),
        "constraint_snapshot": dict(constraints),
    }


def _build_pipeline_summary(intent: ProjectIntent, spec: dict[str, Any]) -> dict[str, Any]:
    return {
        "schema_version": "ctcp-project-generation-pipeline-v1",
        "stages": [
            {"name": "project_intent", "status": "ready", "summary": intent.goal_summary},
            {"name": "spec", "status": "ready", "summary": str(spec.get("problem_to_solve", ""))},
            {"name": "scaffold", "status": "pending", "summary": "project layout and runnable entrypoint"},
            {"name": "core_feature_implementation", "status": "pending", "summary": "business logic for one core user flow"},
            {"name": "smoke_run", "status": "pending", "summary": "prove README + startup path works"},
            {"name": "delivery_package", "status": "pending", "summary": "assemble deliverables for the user"},
        ]
    }


class ProjectBackendService:
    def __init__(self, *, config: BackendConfig, bridge: BridgeAdapter | None = None) -> None:
        self.config = config
        self.job_store = JobStore()
        self.event_bus = EventBus()
        self.question_bus = QuestionBus()
        self.runner = JobRunner(bridge=bridge)

    def create_job(self, request: JobCreateRequest) -> StatusEvent:
        project_spec = _build_project_spec(request.project_intent, request.constraints)
        pipeline_summary = _build_pipeline_summary(request.project_intent, project_spec)
        created = self.runner.create_run(
            goal=request.project_intent.goal_summary or request.user_goal,
            constraints=request.constraints,
            attachments=request.attachments,
            project_intent=request.project_intent.to_payload(),
            project_spec=project_spec,
        )
        run_id = str(created.get("run_id", "")).strip()
        if not run_id:
            run_id = str(created.get("run", "")).strip() or request.request_id
        run_dir = str(created.get("run_dir", "")).strip()
        record = JobRecord(
            job_id=run_id,
            request_id=request.request_id,
            run_id=run_id,
            run_dir=run_dir,
            user_goal=request.user_goal,
            project_intent=request.project_intent.to_payload(),
            project_spec=project_spec,
            pipeline_summary=pipeline_summary,
            constraints=dict(request.constraints),
            phase=JobPhase.CREATED,
        )
        self.job_store.put(record)

        status_event = StatusEvent(
            event_id=new_event_id(),
            job_id=record.job_id,
            phase=JobPhase.CREATED,
            summary=f"project intent accepted: {request.project_intent.goal_summary}",
        )
        self.event_bus.publish(record.job_id, status_event.to_payload())
        self.event_bus.publish(
            record.job_id,
            StatusEvent(
                event_id=new_event_id(),
                job_id=record.job_id,
                phase=JobPhase.PLANNING,
                summary="project spec ready; scaffold/core/smoke/delivery pipeline prepared",
            ).to_payload(),
        )
        if _should_emit_backend_test_default_output(record.constraints):
            done_event = StatusEvent(
                event_id=new_event_id(),
                job_id=record.job_id,
                phase=JobPhase.DONE,
                summary="backend test default output",
            )
            record.phase = JobPhase.DONE
            self.event_bus.publish(record.job_id, done_event.to_payload())
            self.get_result(record.job_id)
            return done_event
        self._sync_status(record.job_id)
        return status_event

    def answer_question(self, answer: JobAnswerRequest) -> StatusEvent:
        record = self.job_store.get(answer.job_id)
        self.runner.answer(
            run_id=record.run_id,
            decision={
                "decision_id": answer.question_id,
                "content": answer.answer_content,
                "answer_meta": answer.answer_meta,
            },
        )
        self.question_bus.clear(record.job_id)
        return self._sync_status(record.job_id)

    def get_status(self, job_id: str) -> StatusEvent:
        return self._sync_status(job_id)

    def get_result(self, job_id: str) -> ResultEvent:
        record = self.job_store.get(job_id)
        report = self.runner.report(run_id=record.run_id)
        try:
            delivery_evidence = self.runner.delivery_evidence(run_id=record.run_id)
        except Exception:
            delivery_evidence = fallback_delivery_evidence(record=record, report=report)
        record.delivery_evidence = dict(delivery_evidence)
        event = ResultEvent(
            event_id=new_event_id(),
            job_id=job_id,
            summary="job result ready",
            artifacts={
                "run_dir": record.run_dir,
                "project_intent": dict(record.project_intent),
                "project_spec": dict(record.project_spec),
                "pipeline_summary": dict(record.pipeline_summary),
                "verify_report": dict(report.get("verify_report", {}) if isinstance(report.get("verify_report", {}), dict) else {}),
                "repo_report_tail": str(report.get("repo_report_tail", "")),
            },
            delivery_evidence=dict(delivery_evidence),
        )
        self.event_bus.publish(job_id, event.to_payload())
        return event

    def poll_events(self, job_id: str) -> list[dict[str, Any]]:
        return self.event_bus.pop_all(job_id)

    def _sync_status(self, job_id: str) -> StatusEvent:
        record = self.job_store.get(job_id)
        try:
            status_doc = self.runner.status(run_id=record.run_id)
        except Exception as exc:
            fail = failure_event(job_id, code="status_error", message=str(exc), details={})
            self.event_bus.publish(job_id, fail.to_payload())
            record.phase = JobPhase.FAILED
            raise

        phase = phase_from_bridge_status(status_doc)
        record.phase = phase
        status_event = StatusEvent(
            event_id=new_event_id(),
            job_id=job_id,
            phase=phase,
            summary=str(dict(status_doc.get("gate", {}) or {}).get("reason", "")).strip() or str(phase.value),
        )
        self.event_bus.publish(job_id, status_event.to_payload())

        decisions_doc = self.runner.decisions(run_id=record.run_id)
        count = int(decisions_doc.get("count", 0) or 0)
        if count > 0:
            rows = decisions_doc.get("decisions", [])
            if isinstance(rows, list) and rows:
                first = rows[0] if isinstance(rows[0], dict) else {}
                question_id = str(first.get("decision_id", "")).strip() or "decision"
                question_text = str(first.get("question_hint", "")).strip() or "need your decision"
                q_event = QuestionEvent(
                    event_id=new_event_id(),
                    job_id=job_id,
                    question_id=question_id,
                    question_text=question_text,
                )
                self.question_bus.set_pending(job_id, question_id=question_id, text=question_text)
                self.event_bus.publish(job_id, q_event.to_payload())

        if phase == JobPhase.DONE:
            self.get_result(job_id)
        return status_event
