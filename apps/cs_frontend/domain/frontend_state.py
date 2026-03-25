from __future__ import annotations

from dataclasses import dataclass


@dataclass
class FrontendState:
    latest_mode: str = "SMALLTALK"
    waiting_question_id: str = ""
