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

from llm_core.providers import api_provider as core_api
from tools.providers import api_agent


class ApiAgentTemplateTests(unittest.TestCase):
    def test_source_generation_api_retry_policy_handles_gateway_timeout(self) -> None:
        request = {
            "role": "chair",
            "action": "source_generation",
            "target_path": "artifacts/source_generation_report.json",
        }
        stderr = "OpenAI API HTTP 504: origin_gateway_timeout retryable true retry_after 120"
        with mock.patch.dict(
            os.environ,
            {
                "CTCP_SOURCE_GENERATION_API_MAX_ATTEMPTS": "3",
                "CTCP_SOURCE_GENERATION_API_RETRY_BASE_DELAY_SEC": "0",
            },
            clear=False,
        ):
            attempts, delay = core_api._agent_retry_policy(request)

        self.assertEqual(attempts, 3)
        self.assertEqual(delay, 0.0)
        self.assertTrue(core_api._is_transient_transport_error(stderr))

    def test_output_contract_freeze_api_retry_policy_handles_gateway_timeout(self) -> None:
        request = {
            "role": "chair",
            "action": "output_contract_freeze",
            "target_path": "artifacts/output_contract_freeze.json",
        }
        stderr = "OpenAI API HTTP 504: origin_gateway_timeout retryable true retry_after 120"
        with mock.patch.dict(
            os.environ,
            {
                "CTCP_OUTPUT_CONTRACT_API_MAX_ATTEMPTS": "3",
                "CTCP_OUTPUT_CONTRACT_API_RETRY_BASE_DELAY_SEC": "0",
            },
            clear=False,
        ):
            attempts, delay = core_api._agent_retry_policy(request)

        self.assertEqual(attempts, 3)
        self.assertEqual(delay, 0.0)
        self.assertTrue(core_api._is_transient_transport_error(stderr))

    def test_agent_phase_retries_empty_payload_when_stderr_is_transient(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = Path(td) / "run"
            logs_dir = run_dir / "logs"
            repo_root.mkdir(parents=True, exist_ok=True)
            logs_dir.mkdir(parents=True, exist_ok=True)
            counter_path = run_dir / "counter.txt"
            agent_script = repo_root / "agent_empty_then_json.py"
            agent_script.write_text(
                "\n".join(
                    [
                        "from pathlib import Path",
                        "import sys",
                        f"counter = Path(r'{counter_path}')",
                        "value = int(counter.read_text() or '0') if counter.exists() else 0",
                        "counter.write_text(str(value + 1))",
                        "if value == 0:",
                        "    print('OpenAI API request failed: tlsv1 alert protocol version', file=sys.stderr)",
                        "else:",
                        "    print('{\"schema_version\":\"ctcp-provider-source-files-v1\",\"files\":[]}')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            def normalize_target_payload(**kwargs: object) -> tuple[str, str]:
                raw = str(kwargs.get("raw_text", "")).strip()
                try:
                    doc = json.loads(raw)
                except Exception:
                    return "", "agent output is not valid JSON object"
                return json.dumps(doc), ""

            hooks = core_api.ApiProviderHooks(
                resolve_templates=lambda repo_root, config: ({}, ""),
                build_evidence_pack=lambda **kwargs: {},
                render_prompt=lambda **kwargs: "",
                record_failure_review=lambda run_dir, reason: Path(run_dir) / "reviews" / "failure.md",
                needs_patch=lambda request: False,
                normalize_patch_payload=lambda text: (text, ""),
                normalize_target_payload=normalize_target_payload,
            )

            with mock.patch.dict(
                os.environ,
                {
                    "CTCP_SOURCE_GENERATION_API_MAX_ATTEMPTS": "3",
                    "CTCP_SOURCE_GENERATION_API_RETRY_BASE_DELAY_SEC": "0",
                },
                clear=False,
            ):
                result = core_api._run_agent_phase(
                    template=f'"{sys.executable}" "{agent_script}"',
                    placeholders={},
                    repo_root=repo_root,
                    run_dir=run_dir,
                    logs_dir=logs_dir,
                    prompt_text="prompt",
                    api_call_env={},
                    hooks=hooks,
                    request={"role": "chair", "action": "source_generation", "target_path": "artifacts/source_generation_report.json"},
                    target_path=run_dir / "artifacts" / "source_generation_report.json",
                    target_rel="artifacts/source_generation_report.json",
                    prompt_path=run_dir / "outbox" / "prompt.md",
                )

            self.assertEqual(result.get("status"), "executed", msg=str(result))
            self.assertEqual(counter_path.read_text(encoding="utf-8"), "2")
            self.assertTrue((run_dir / "artifacts" / "source_generation_report.json").exists())
            retry_log = (logs_dir / "agent_retry.jsonl").read_text(encoding="utf-8")
            self.assertIn("transient_transport_error_after_empty_payload", retry_log)

    def test_json_target_requests_json_object_response_format(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            env = core_api._build_api_call_env(
                run_dir=run_dir,
                request={"role": "chair", "action": "source_generation", "target_path": "artifacts/source_generation_report.json"},
            )

        self.assertEqual(env.get("SDDAI_OPENAI_RESPONSE_FORMAT"), "json_object")

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

    def test_gptsapi_notes_base_url_normalizes_without_v1(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "",
                "CTCP_OPENAI_API_KEY": "",
                "OPENAI_BASE_URL": "",
                "CTCP_OPENAI_BASE_URL": "",
            },
            clear=False,
        ), mock.patch.object(
            api_agent,
            "_load_local_notes_defaults",
            return_value={"api_key": "sk-notes", "base_url": "https://api.gptsapi.net/v1"},
        ):
            key, base_url = api_agent._resolved_external_api_credentials()

        self.assertEqual(key, "sk-notes")
        self.assertEqual(base_url, "https://api.gptsapi.net")

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

    def test_execute_plan_only_flattens_multiline_goal_and_reason_for_shell_command(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            plan_script = repo_root / "plan_args_stub.py"
            plan_script.write_text(
                "\n".join(
                    [
                        "import sys",
                        "goal = sys.argv[1]",
                        "reason = sys.argv[2]",
                        "assert '\\n' not in goal and '\\r' not in goal",
                        "assert '\\n' not in reason and '\\r' not in reason",
                        "print('# PLAN')",
                        "print(f'Goal: {goal}')",
                        "print(f'Reason: {reason}')",
                        "",
                    ]
                ),
                encoding="utf-8",
            )

            request = {
                "role": "chair",
                "action": "plan_draft",
                "target_path": "artifacts/analysis.md",
                "reason": "waiting for analysis.md\nand planner retry",
                "goal": "第一行需求\n第二行需求\n第三行需求",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "SDDAI_PLAN_CMD": f'"{sys.executable}" "{plan_script}" "{{GOAL}}" "{{REASON}}"',
                    "SDDAI_AGENT_CMD": "",
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
            target = run_dir / "artifacts" / "analysis.md"
            text = target.read_text(encoding="utf-8")
            self.assertIn("Goal: 第一行需求 第二行需求 第三行需求", text)
            self.assertIn("Reason: waiting for analysis.md and planner retry", text)

    def test_execute_plan_only_records_analysis_failure_when_plan_command_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            fail_script = repo_root / "plan_fail.py"
            fail_script.write_text("import sys\nsys.exit(1)\n", encoding="utf-8")

            request = {
                "role": "chair",
                "action": "plan_draft",
                "target_path": "artifacts/analysis.md",
                "reason": "waiting for analysis.md",
                "goal": "做一个上传 CSV 并导出结果的本地轻应用",
            }
            with mock.patch.dict(
                os.environ,
                {
                    "SDDAI_PLAN_CMD": f'"{sys.executable}" "{fail_script}"',
                    "SDDAI_AGENT_CMD": "",
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

            self.assertEqual(result.get("status"), "exec_failed", msg=str(result))
            self.assertIn("analysis provider command failed", str(result.get("reason", "")))
            self.assertFalse((run_dir / "artifacts" / "analysis.md").exists())
            progress_path = run_dir / "artifacts" / "analysis_progress.json"
            self.assertTrue(progress_path.exists())
            progress = json.loads(progress_path.read_text(encoding="utf-8"))
            self.assertEqual(progress.get("status"), "failed")
            self.assertEqual(progress.get("last_event"), "provider_call_failed")

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

            self.assertEqual(result.get("status"), "exec_failed", msg=str(result))
            self.assertIn("formal_api_only", str(result.get("reason", "")))
            target = run_dir / "artifacts" / "file_request.json"
            self.assertFalse(target.exists())

    def test_execute_file_request_expands_narrative_project_context_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            agent_script = repo_root / "agent_stub_narrative_ctx.py"
            agent_script.write_text("print('not json')\n", encoding="utf-8")

            request = {
                "role": "chair",
                "action": "file_request",
                "target_path": "artifacts/file_request.json",
                "reason": "waiting for file_request.json",
                "goal": (
                    "我想要生成一个可以帮助创作者制作叙事项目的助手。"
                    "它需要处理故事线、角色关系、章节结构和提示词导出。"
                ),
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

            self.assertEqual(result.get("status"), "exec_failed", msg=str(result))
            self.assertIn("formal_api_only", str(result.get("reason", "")))
            target = run_dir / "artifacts" / "file_request.json"
            self.assertFalse(target.exists())

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

    def test_execute_context_pack_falls_back_to_file_request_materialization_when_model_output_has_no_json(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            repo_root = Path(td) / "repo"
            run_dir = repo_root / "runs" / "r1"
            repo_root.mkdir(parents=True, exist_ok=True)
            run_dir.mkdir(parents=True, exist_ok=True)

            (repo_root / "README.md").write_text("# Demo\nHello context pack\n", encoding="utf-8")
            (repo_root / "docs").mkdir(parents=True, exist_ok=True)
            (repo_root / "docs" / "guide.md").write_text("line1\nline2\nline3\nline4\n", encoding="utf-8")
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "file_request.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-file-request-v1",
                        "goal": "fallback context pack",
                        "needs": [
                            {"path": "README.md", "mode": "full"},
                            {"path": "docs/guide.md", "mode": "snippets", "line_ranges": [[2, 3]]},
                        ],
                        "budget": {"max_files": 4, "max_total_bytes": 4096},
                        "reason": "collect repo context",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )

            agent_script = repo_root / "agent_stub_ctx_empty.py"
            agent_script.write_text("print('plain text without json structure')\n", encoding="utf-8")

            request = {
                "role": "librarian",
                "action": "context_pack",
                "target_path": "artifacts/context_pack.json",
                "reason": "waiting for context_pack.json",
                "goal": "fallback context pack",
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
            self.assertTrue(target.exists())
            doc = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(doc.get("schema_version"), "ctcp-context-pack-v1")
            self.assertTrue([row for row in doc.get("files", []) if isinstance(row, dict)])

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

    def test_render_prompt_for_source_generation_requests_file_content_bundle(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "output_contract_freeze.json").write_text(
                json.dumps(
                    {
                        "project_root": "project_output/vn",
                        "startup_entrypoint": "project_output/vn/scripts/run_project_gui.py",
                        "startup_readme": "project_output/vn/README.md",
                        "source_files": [
                            "project_output/vn/pyproject.toml",
                            "project_output/vn/src/vn/__init__.py",
                        ],
                        "business_files": ["project_output/vn/src/vn/service.py"],
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            evidence: dict[str, Path] = {}
            for key in ("context", "constraints", "fix_brief", "externals"):
                p = run_dir / f"{key.upper()}.md"
                p.write_text(f"# {key}\n- sample\n", encoding="utf-8")
                evidence[key] = p

            prompt = api_agent._render_prompt(
                run_dir=run_dir,
                repo_root=repo_root,
                request={
                    "role": "chair",
                    "action": "source_generation",
                    "goal": "VN assistant",
                    "target_path": "artifacts/source_generation_report.json",
                },
                evidence=evidence,
            )

            for token in (
                "ctcp-provider-source-files-v1", '"files"', '"path"', '"content_lines"',
                "project_output/vn/scripts/run_project_gui.py", "project_output/vn/src/vn/service.py",
                "project_output/vn/pyproject.toml", "project_output/vn/src/vn/__init__.py",
                "tkinter", "do not import PyQt5", "from vn.service", "cross-file import/export checklist",
                "interfaces", "public `defines`, `imports`, and `exports`", "target file must define that exact helper",
                "every imported symbol resolves", "startup entrypoint constructs a service/controller",
                "launcher compatibility table", "*args`/`**kwargs", "Do not ship TODO, placeholder, stub, pass-only",
                "never put literal line breaks inside a JSON string", "--headless", "--goal --project-name --out --headless",
                "workspace_preview.html", "interaction_trace.json", "do not write f-strings or quoted strings split across physical lines",
                "join(lines)", "content_items", "project must declare its own concrete acceptance criteria", "verifier does not run `pip install`",
                "standard-library `http.server`", "do not import Flask", "`--serve` and the rich export command must exit 0",
                "virtual-team handoff", "Integration QA checks every import/export and call signature",
                "do not use bare sibling imports", "`import service`", "API signature matrix",
                "`## Project Overview`", "real `/` HTML page plus `/status`",
            ):
                self.assertIn(token, prompt)

    def test_render_prompt_for_source_generation_includes_previous_failure_feedback(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td) / "run"
            repo_root = Path(td) / "repo"
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            repo_root.mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "output_contract_freeze.json").write_text(
                json.dumps({"project_root": "project_output/vn", "startup_entrypoint": "project_output/vn/scripts/run_project_gui.py"}, ensure_ascii=False),
                encoding="utf-8",
            )
            (run_dir / "artifacts" / "source_generation_report.json").write_text(
                json.dumps(
                    {
                        "status": "blocked",
                        "generic_validation": {
                            "smoke_run": {
                                "startup_probe": {"stderr_tail": "ModuleNotFoundError: No module named 'service'"},
                                "export_probe": {
                                    "stdout_tail": (
                                        "TypeError: CommandWhitelist.__init__() missing 1 required positional argument: 'commands'\n"
                                        "/status URLError <urlopen error timed out>"
                                    )
                                },
                            },
                            "python_import_consistency": {
                                "missing_symbols": [
                                    {
                                        "from_path": "project_output/vn/src/vn/story/__init__.py",
                                        "target_path": "project_output/vn/src/vn/story/outline.py",
                                        "symbol": "StoryOutline",
                                    }
                                ]
                            },
                        },
                        "domain_validation": {"missing": ["project-defined acceptance criteria missing"]},
                        "readme_quality": {"missing_sections": ["how_to_run", "directory_map"], "reasons": ["README missing sections: how_to_run, directory_map"]},
                        "ux_validation": {"reasons": ["visual evidence files missing"]},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            evidence: dict[str, Path] = {}
            for key in ("context", "constraints", "fix_brief", "externals"):
                p = run_dir / f"{key.upper()}.md"
                p.write_text(f"# {key}\n- sample\n", encoding="utf-8")
                evidence[key] = p

            prompt = api_agent._render_prompt(
                run_dir=run_dir,
                repo_root=repo_root,
                request={
                    "role": "chair",
                    "action": "source_generation",
                    "goal": "VN assistant",
                    "target_path": "artifacts/source_generation_report.json",
                },
                evidence=evidence,
            )

            for token in (
                "Previous source_generation failed", "No module named 'service'",
                "validation probes do not install dependencies", "bare sibling import inside a src-layout package",
                "CommandWhitelist.__init__", "constructor or method signature mismatch",
                "local server did not become reachable", "StoryOutline",
                "project-defined acceptance criteria missing", "how_to_run", "directory_map",
                "README missing sections", "visual evidence files missing",
            ):
                self.assertIn(token, prompt)

if __name__ == "__main__":
    unittest.main()
