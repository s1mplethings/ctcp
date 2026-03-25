from __future__ import annotations

import unittest

from contracts.schemas.job_answer import JobAnswerRequest
from contracts.schemas.job_create import JobCreateRequest
from shared.errors import ValidationContractError


class ContractValidationTests(unittest.TestCase):
    def test_job_create_accepts_structured_payload(self) -> None:
        request = JobCreateRequest.from_payload(
            {
                "request_id": "req-1",
                "user_goal": "build project backend",
                "constraints": {"runtime_target": "offline"},
                "attachments": ["a.txt"],
                "requirement_summary": {"mode": "PROJECT_DETAIL"},
            }
        )
        self.assertEqual(request.request_id, "req-1")
        self.assertEqual(request.user_goal, "build project backend")

    def test_job_create_rejects_full_chat_history_field(self) -> None:
        with self.assertRaises(ValidationContractError):
            JobCreateRequest.from_payload(
                {
                    "request_id": "req-2",
                    "user_goal": "build project backend",
                    "chat_history": [{"role": "user", "content": "full transcript"}],
                }
            )

    def test_job_create_rejects_nested_full_chat_history_field(self) -> None:
        with self.assertRaises(ValidationContractError):
            JobCreateRequest.from_payload(
                {
                    "request_id": "req-2b",
                    "user_goal": "build project backend",
                    "requirement_summary": {
                        "mode": "PROJECT_DETAIL",
                        "context": {
                            "chat_history": [{"role": "user", "content": "full transcript"}],
                        },
                    },
                }
            )

    def test_job_answer_requires_question_id(self) -> None:
        with self.assertRaises(ValidationContractError):
            JobAnswerRequest.from_payload(
                {
                    "request_id": "req-3",
                    "job_id": "job-1",
                    "answer_content": "yes",
                }
            )


if __name__ == "__main__":
    unittest.main()
