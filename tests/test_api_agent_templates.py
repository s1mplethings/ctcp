#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers import api_agent


class ApiAgentTemplateTests(unittest.TestCase):
    def test_ollama_placeholder_key_requires_base_url_for_api_mode(self) -> None:
        request = {
            "role": "chair",
            "action": "plan_draft",
            "target_path": "artifacts/PLAN_draft.md",
        }
        with mock.patch.dict(
            os.environ,
            {
                "SDDAI_PLAN_CMD": "",
                "SDDAI_AGENT_CMD": "",
                "SDDAI_PATCH_CMD": "",
                "OPENAI_API_KEY": "ollama",
                "CTCP_OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
                "CTCP_OPENAI_BASE_URL": "",
            },
            clear=False,
        ), mock.patch.object(api_agent, "_load_local_notes_defaults", return_value={}):
            templates, reason = api_agent._resolve_templates(ROOT, request)

        self.assertEqual(templates, {})
        self.assertIn("OPENAI_BASE_URL", reason)

    def test_ollama_placeholder_key_falls_back_to_local_notes_credentials(self) -> None:
        request = {
            "role": "support_lead",
            "action": "reply",
            "target_path": "artifacts/support_reply.provider.json",
        }
        with mock.patch.dict(
            os.environ,
            {
                "SDDAI_PLAN_CMD": "",
                "SDDAI_AGENT_CMD": "",
                "SDDAI_PATCH_CMD": "",
                "OPENAI_API_KEY": "ollama",
                "CTCP_OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
                "CTCP_OPENAI_BASE_URL": "",
            },
            clear=False,
        ), mock.patch.object(
            api_agent,
            "_load_local_notes_defaults",
            return_value={"api_key": "sk-notes", "base_url": "https://notes.example/v1"},
        ):
            templates, reason = api_agent._resolve_templates(ROOT, request)

        self.assertEqual(reason, "")
        self.assertIn("agent", templates)

    def test_resolve_templates_plan_only_includes_agent_key(self) -> None:
        request = {
            "role": "chair",
            "action": "plan_draft",
            "target_path": "artifacts/PLAN_draft.md",
        }
        with mock.patch.dict(
            os.environ,
            {
                "SDDAI_PLAN_CMD": "echo plan",
                "SDDAI_AGENT_CMD": "",
                "SDDAI_PATCH_CMD": "",
                "OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
            },
            clear=False,
        ):
            templates, reason = api_agent._resolve_templates(ROOT, request)

        self.assertEqual(reason, "")
        self.assertIn("plan", templates)
        self.assertIn("agent", templates)
        self.assertEqual(templates["agent"], templates["plan"])

    def test_execute_plan_only_chair_writes_target_without_keyerror(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            plan_script = repo_root / "plan_stub.py"
            plan_script.write_text(
                "\n".join(
                    [
                        "print('# PLAN')",
                        "print('Status: DRAFT')",
                        "print('- step: chair')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            env = {
                "SDDAI_PLAN_CMD": f'"{sys.executable}" "{plan_script}"',
                "SDDAI_AGENT_CMD": "",
                "SDDAI_PATCH_CMD": "",
                "OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
            }
            cases = (
                ("plan_draft", "artifacts/PLAN_draft.md", "waiting for PLAN_draft.md", "Status: DRAFT"),
                ("plan_signed", "artifacts/PLAN.md", "waiting for PLAN.md", "Status: SIGNED"),
            )
            for action, target_path, reason, expected_status in cases:
                request = {
                    "role": "chair",
                    "action": action,
                    "target_path": target_path,
                    "reason": reason,
                    "goal": "generate chair plan",
                }
                with mock.patch.dict(os.environ, env, clear=False):
                    result = api_agent.execute(
                        repo_root=repo_root,
                        run_dir=run_dir,
                        request=request,
                        config={"budgets": {"max_outbox_prompts": 8}},
                        guardrails_budgets={},
                    )

                self.assertEqual(result.get("status"), "executed", msg=str(result))
                target = run_dir / target_path
                self.assertTrue(target.exists(), msg=str(result))
                self.assertIn(expected_status, target.read_text(encoding="utf-8"))

    def test_execute_file_request_normalizes_non_json_output(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            agent_script = repo_root / "agent_stub.py"
            agent_script.write_text(
                "\n".join(
                    [
                        "print('# file request draft')",
                        "print('- no json provided')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            request = {
                "role": "chair",
                "action": "file_request",
                "target_path": "artifacts/file_request.json",
                "reason": "waiting for file_request.json",
                "goal": "normalize json output",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "SDDAI_AGENT_CMD": f'"{sys.executable}" "{agent_script}"',
                    "SDDAI_PLAN_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                    "OPENAI_API_KEY": "",
                    "OPENAI_BASE_URL": "",
                },
                clear=False,
            ):
                result = api_agent.execute(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    request=request,
                    config={"budgets": {"max_outbox_prompts": 8}},
                    guardrails_budgets={},
                )

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            target = run_dir / "artifacts" / "file_request.json"
            doc = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(doc.get("schema_version"), "ctcp-file-request-v1")
            self.assertIsInstance(doc.get("needs"), list)
            self.assertIsInstance(doc.get("budget"), dict)
            self.assertIn("reason", doc)

    def test_execute_context_pack_normalizes_partial_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            agent_script = repo_root / "agent_stub_ctx.py"
            agent_script.write_text(
                "\n".join(
                    [
                        "import json",
                        "print(json.dumps({'summary': 'partial'}))",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            request = {
                "role": "librarian",
                "action": "context_pack",
                "target_path": "artifacts/context_pack.json",
                "reason": "waiting for context_pack.json",
                "goal": "normalize context pack",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "SDDAI_AGENT_CMD": f'"{sys.executable}" "{agent_script}"',
                    "SDDAI_PLAN_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                    "OPENAI_API_KEY": "",
                    "OPENAI_BASE_URL": "",
                },
                clear=False,
            ):
                result = api_agent.execute(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    request=request,
                    config={"budgets": {"max_outbox_prompts": 8}},
                    guardrails_budgets={},
                )

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            target = run_dir / "artifacts" / "context_pack.json"
            doc = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(doc.get("schema_version"), "ctcp-context-pack-v1")
            self.assertIsInstance(doc.get("files"), list)
            self.assertIsInstance(doc.get("omitted"), list)
            self.assertTrue(str(doc.get("summary", "")).strip())

    def test_execute_guardrails_normalizes_required_keys(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            agent_script = repo_root / "agent_stub_guardrails.py"
            agent_script.write_text(
                "\n".join(
                    [
                        "print('# not key-value')",
                        "print('this output should be normalized')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            request = {
                "role": "chair",
                "action": "plan_draft",
                "target_path": "artifacts/guardrails.md",
                "reason": "waiting for guardrails.md",
                "goal": "normalize guardrails output",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "SDDAI_AGENT_CMD": f'"{sys.executable}" "{agent_script}"',
                    "SDDAI_PLAN_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                    "OPENAI_API_KEY": "",
                    "OPENAI_BASE_URL": "",
                    "CTCP_OPENAI_API_KEY": "",
                    "CTCP_LOCAL_NOTES_PATH": str(run_dir / "missing_notes.md"),
                },
                clear=False,
            ):
                result = api_agent.execute(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    request=request,
                    config={"budgets": {"max_outbox_prompts": 8}},
                    guardrails_budgets={},
                )

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            text = (run_dir / "artifacts" / "guardrails.md").read_text(encoding="utf-8")
            self.assertIn("find_mode:", text)
            self.assertIn("max_files:", text)
            self.assertIn("max_total_bytes:", text)
            self.assertIn("max_iterations:", text)

    def test_execute_support_reply_recovers_non_utf8_child_stdout(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            agent_script = repo_root / "agent_stub_support_gbk.py"
            agent_script.write_text(
                "\n".join(
                    [
                        "import json, sys",
                        "payload = {",
                        "    'reply_text': '你好，我已经接住这轮需求。',",
                        "    'next_question': '你最想先推进哪一块？',",
                        "    'actions': [],",
                        "    'debug_notes': 'gbk-child-test',",
                        "}",
                        "sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False).encode('gbk'))",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            request = {
                "role": "support_lead",
                "action": "reply",
                "target_path": "artifacts/support_reply.provider.json",
                "reason": "write support reply json",
                "goal": "support session smoke",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "SDDAI_AGENT_CMD": f'"{sys.executable}" "{agent_script}"',
                    "SDDAI_PLAN_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                    "OPENAI_API_KEY": "",
                    "OPENAI_BASE_URL": "",
                    "CTCP_OPENAI_API_KEY": "",
                    "CTCP_LOCAL_NOTES_PATH": str(run_dir / "missing_notes.md"),
                },
                clear=False,
            ):
                result = api_agent.execute(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    request=request,
                    config={"budgets": {"max_outbox_prompts": 8}},
                    guardrails_budgets={},
                )

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            target = run_dir / "artifacts" / "support_reply.provider.json"
            doc = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(doc.get("reply_text"), "你好，我已经接住这轮需求。")
            self.assertEqual(doc.get("next_question"), "你最想先推进哪一块？")

    def test_execute_review_normalizes_verdict_contract(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            agent_script = repo_root / "agent_stub_review.py"
            agent_script.write_text(
                "\n".join(
                    [
                        "print('# random review text')",
                        "print('- looks mostly fine')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            request = {
                "role": "contract_guardian",
                "action": "review_contract",
                "target_path": "reviews/review_contract.md",
                "reason": "waiting for review_contract.md",
                "goal": "normalize review output",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "SDDAI_AGENT_CMD": f'"{sys.executable}" "{agent_script}"',
                    "SDDAI_PLAN_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                    "OPENAI_API_KEY": "",
                    "OPENAI_BASE_URL": "",
                    "CTCP_OPENAI_API_KEY": "",
                    "CTCP_LOCAL_NOTES_PATH": str(run_dir / "missing_notes.md"),
                },
                clear=False,
            ):
                result = api_agent.execute(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    request=request,
                    config={"budgets": {"max_outbox_prompts": 8}},
                    guardrails_budgets={},
                )

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            text = (run_dir / "reviews" / "review_contract.md").read_text(encoding="utf-8")
            self.assertIn("Verdict:", text)
            self.assertIn("Blocking Reasons:", text)
            self.assertIn("Required Fix/Artifacts:", text)

    def test_execute_plan_signed_normalizes_status(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            agent_script = repo_root / "agent_stub_plan_signed.py"
            agent_script.write_text("print('# noisy plan')\n", encoding="utf-8")

            request = {
                "role": "chair",
                "action": "plan_signed",
                "target_path": "artifacts/PLAN.md",
                "reason": "waiting for signed PLAN.md",
                "goal": "normalize plan signed",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "SDDAI_AGENT_CMD": f'"{sys.executable}" "{agent_script}"',
                    "SDDAI_PLAN_CMD": "",
                    "SDDAI_PATCH_CMD": "",
                    "OPENAI_API_KEY": "",
                    "OPENAI_BASE_URL": "",
                    "CTCP_OPENAI_API_KEY": "",
                    "CTCP_LOCAL_NOTES_PATH": str(run_dir / "missing_notes.md"),
                },
                clear=False,
            ):
                result = api_agent.execute(
                    repo_root=repo_root,
                    run_dir=run_dir,
                    request=request,
                    config={"budgets": {"max_outbox_prompts": 8}},
                    guardrails_budgets={},
                )

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            text = (run_dir / "artifacts" / "PLAN.md").read_text(encoding="utf-8")
            self.assertIn("Status: SIGNED", text)

    def test_render_prompt_includes_whiteboard_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            run_dir.mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)

            evidence: dict[str, Path] = {}
            for key in ("context", "constraints", "fix_brief", "externals"):
                p = run_dir / f"{key.upper()}.md"
                p.write_text(f"# {key}\n- sample\n", encoding="utf-8")
                evidence[key] = p

            request = {
                "role": "patchmaker",
                "action": "make_patch",
                "goal": "support and production shared whiteboard",
                "reason": "waiting for diff.patch",
                "target_path": "artifacts/diff.patch",
                "whiteboard": {
                    "path": "artifacts/support_whiteboard.json",
                    "query": "support and production shared whiteboard",
                    "hits": [
                        {
                            "path": "docs/10_team_mode.md",
                            "start_line": 42,
                            "snippet": "support and production collaboration lane",
                        }
                    ],
                    "snapshot": {
                        "entries": [
                            {
                                "role": "support_lead",
                                "kind": "dispatch_request",
                                "text": "sync requirement to production lane",
                            }
                        ]
                    },
                },
            }

            prompt = api_agent._render_prompt(
                run_dir=run_dir,
                repo_root=repo_root,
                request=request,
                evidence=evidence,
            )
            self.assertIn("# WHITEBOARD", prompt)
            self.assertIn("artifacts/support_whiteboard.json", prompt)
            self.assertIn("librarian_query", prompt)
            self.assertIn("docs/10_team_mode.md", prompt)
            self.assertIn("[support_lead/dispatch_request]", prompt)


if __name__ == "__main__":
    unittest.main()
