from __future__ import annotations

from apps.cs_frontend.application.answer_question import answer_question as call_answer_question
from apps.cs_frontend.application.create_job import create_job as call_create_job
from apps.cs_frontend.application.handle_backend_event import handle_backend_event
from apps.cs_frontend.config import FrontendConfig
from apps.cs_frontend.dialogue.intent_router import IntentRouter
from apps.cs_frontend.dialogue.question_manager import QuestionManager
from apps.cs_frontend.dialogue.requirement_collector import RequirementCollector
from apps.cs_frontend.dialogue.response_renderer import ResponseRenderer
from apps.cs_frontend.dialogue.session_manager import SessionManager
from apps.cs_frontend.domain.presentable_event import PresentableEvent
from apps.cs_frontend.gateway.backend_client import BackendClient
from apps.cs_frontend.gateway.dto_mapper import DtoMapper
from apps.cs_frontend.storage.pending_question_store import PendingQuestionStore
from apps.cs_frontend.storage.session_store import SessionStore


class FrontendMessageHandler:
    def __init__(
        self,
        *,
        config: FrontendConfig,
        backend_client: BackendClient,
        session_store: SessionStore,
        pending_question_store: PendingQuestionStore,
    ) -> None:
        self.config = config
        self.backend_client = backend_client
        self.session_manager = SessionManager(session_store)
        self.intent_router = IntentRouter()
        self.requirement_collector = RequirementCollector()
        self.question_manager = QuestionManager()
        self.response_renderer = ResponseRenderer()
        self.dto_mapper = DtoMapper()
        self.pending_store = pending_question_store

    def handle_user_message(self, *, session_id: str, text: str, source: str) -> PresentableEvent:
        session = self.session_manager.get_or_create(session_id)
        user_text = str(text or "").strip()
        history = list(session.history_summary)

        pending = self.pending_store.get(session_id)
        if pending and session.active_job_id:
            payload = self.dto_mapper.to_job_answer_payload(
                job_id=session.active_job_id,
                question_id=str(pending.get("question_id", "")),
                answer=user_text,
            )
            call_answer_question(self.backend_client, payload)
            self.pending_store.clear(session_id)
            events = self.backend_client.poll_events(session.active_job_id)
            self.session_manager.remember_turn(session, user_text)
            return handle_backend_event(
                renderer=self.response_renderer,
                pending_store=self.pending_store,
                session_id=session_id,
                events=events,
            )

        mode = self.intent_router.route(
            latest_user_text=user_text,
            history=history + [user_text],
            active_state={"task_summary": session.history_summary[-1] if session.history_summary else ""},
        )
        session.latest_mode = mode
        requirement = self.requirement_collector.collect(mode=mode, latest_user_text=user_text, history=history + [user_text])

        if not session.active_job_id and bool(requirement.get("is_project_like", False)):
            payload = self.dto_mapper.to_job_create_payload(user_goal=user_text, requirement_summary=requirement)
            create_event = call_create_job(self.backend_client, payload)
            session.active_job_id = str(create_event.get("job_id", "")).strip()
            self.session_manager.remember_turn(session, user_text)
            events = self.backend_client.poll_events(session.active_job_id)
            return handle_backend_event(
                renderer=self.response_renderer,
                pending_store=self.pending_store,
                session_id=session_id,
                events=events,
            )

        if session.active_job_id:
            self.backend_client.get_status(session.active_job_id)
            events = self.backend_client.poll_events(session.active_job_id)
            self.session_manager.remember_turn(session, user_text)
            rendered = handle_backend_event(
                renderer=self.response_renderer,
                pending_store=self.pending_store,
                session_id=session_id,
                events=events,
            )
            if events:
                return rendered

        self.session_manager.remember_turn(session, user_text)
        if self.pending_store.get(session_id):
            q = self.pending_store.get(session_id) or {}
            return PresentableEvent(reply_text=self.question_manager.render_question(q), events=[])

        if mode in {"GREETING", "SMALLTALK", "CAPABILITY_QUERY"}:
            return PresentableEvent(reply_text="收到，我是客服前端入口，先帮你整理需求再发后端执行。", events=[])
        return PresentableEvent(reply_text="我先把你的需求整理成结构化任务，然后交给后端继续执行。", events=[])
