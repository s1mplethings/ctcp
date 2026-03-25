from __future__ import annotations

from apps.cs_frontend.application.handle_user_message import FrontendMessageHandler
from apps.cs_frontend.config import FrontendConfig
from apps.cs_frontend.gateway.backend_client import BackendClient
from apps.cs_frontend.storage.pending_question_store import PendingQuestionStore
from apps.cs_frontend.storage.session_store import SessionStore


def bootstrap_frontend(
    *,
    backend_client: BackendClient | None = None,
    config: FrontendConfig | None = None,
) -> FrontendMessageHandler:
    return FrontendMessageHandler(
        config=config or FrontendConfig(),
        backend_client=backend_client or BackendClient(),
        session_store=SessionStore(),
        pending_question_store=PendingQuestionStore(),
    )
