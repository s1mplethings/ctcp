#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from tools.providers import ollama_agent


class OllamaAgentTests(unittest.TestCase):
    def test_start_ollama_service_on_windows_avoids_run_dir_log_handle_lock(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with mock.patch("tools.providers.ollama_agent.os.name", "nt"), mock.patch.object(
                ollama_agent.subprocess,
                "CREATE_NEW_PROCESS_GROUP",
                0x200,
                create=True,
            ), mock.patch.object(
                ollama_agent.subprocess,
                "DETACHED_PROCESS",
                0x008,
                create=True,
            ), mock.patch.object(ollama_agent.subprocess, "Popen") as popen:
                ok, err = ollama_agent._start_ollama_service(cmd="ollama serve", run_dir=run_dir)
                log_text = (run_dir / "logs" / "ollama_serve.log").read_text(encoding="utf-8")

        self.assertTrue(ok, msg=err)
        self.assertEqual(err, "")
        kwargs = dict(popen.call_args.kwargs)
        self.assertIs(kwargs.get("stdout"), ollama_agent.subprocess.DEVNULL)
        self.assertIs(kwargs.get("stderr"), ollama_agent.subprocess.DEVNULL)
        self.assertIn("avoid locking the run directory on Windows", log_text)

    def test_preview_librarian_context_pack_reports_local_model_metadata(self) -> None:
        request = {
            "role": "librarian",
            "action": "context_pack",
            "target_path": "artifacts/context_pack.json",
        }
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with mock.patch.object(
                ollama_agent,
                "_ensure_ollama_ready",
                return_value=(True, ""),
            ) as ensure_ready, mock.patch.object(ollama_agent.api_agent, "preview") as api_preview:
                out = ollama_agent.preview(run_dir=run_dir, request=request, config={})

        self.assertEqual(out.get("status"), "can_exec", msg=str(out))
        self.assertEqual(out.get("provider_mode"), "local")
        self.assertEqual(out.get("fallback_blocked"), True)
        self.assertTrue(str(out.get("model_name", "")).strip())
        ensure_ready.assert_called_once()
        api_preview.assert_not_called()

    def test_preview_returns_disabled_when_autostart_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with mock.patch.dict(
                os.environ,
                {"SDDAI_AGENT_CMD": "", "SDDAI_PLAN_CMD": "", "SDDAI_PATCH_CMD": ""},
                clear=False,
            ):
                with mock.patch.object(
                    ollama_agent,
                    "_ensure_ollama_ready",
                    return_value=(False, "bootstrap failed"),
                ) as ensure_ready:
                    with mock.patch.object(ollama_agent.api_agent, "preview") as api_preview:
                        out = ollama_agent.preview(run_dir=run_dir, request={}, config={})

            self.assertEqual(out.get("status"), "disabled", msg=str(out))
            self.assertIn("bootstrap failed", str(out.get("reason", "")))
            self.assertEqual(out.get("runtime"), "ollama")
            ensure_ready.assert_called_once()
            api_preview.assert_not_called()

    def test_preview_skips_bootstrap_when_custom_cmd_is_set(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with mock.patch.dict(
                os.environ,
                {"SDDAI_AGENT_CMD": "echo custom", "SDDAI_PLAN_CMD": "", "SDDAI_PATCH_CMD": ""},
                clear=False,
            ):
                with mock.patch.object(ollama_agent, "_ensure_ollama_ready") as ensure_ready:
                    with mock.patch.object(
                        ollama_agent.api_agent,
                        "preview",
                        return_value={"status": "can_exec"},
                    ) as api_preview:
                        out = ollama_agent.preview(run_dir=run_dir, request={}, config={})

            self.assertEqual(out.get("status"), "can_exec", msg=str(out))
            self.assertEqual(out.get("runtime"), "ollama")
            ensure_ready.assert_not_called()
            api_preview.assert_called_once()

    def test_execute_returns_exec_failed_when_autostart_fails(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with mock.patch.dict(
                os.environ,
                {"SDDAI_AGENT_CMD": "", "SDDAI_PLAN_CMD": "", "SDDAI_PATCH_CMD": ""},
                clear=False,
            ):
                with mock.patch.object(
                    ollama_agent,
                    "_ensure_ollama_ready",
                    return_value=(False, "cannot reach ollama"),
                ) as ensure_ready:
                    with mock.patch.object(ollama_agent.api_agent, "execute") as api_execute:
                        out = ollama_agent.execute(
                            repo_root=ROOT,
                            run_dir=run_dir,
                            request={},
                            config={},
                            guardrails_budgets={},
                        )

            self.assertEqual(out.get("status"), "exec_failed", msg=str(out))
            self.assertIn("cannot reach ollama", str(out.get("reason", "")))
            self.assertEqual(out.get("runtime"), "ollama")
            ensure_ready.assert_called_once()
            api_execute.assert_not_called()

    def test_execute_support_reply_uses_native_chat_api(self) -> None:
        class _Response:
            def __init__(self, payload: dict[str, object]) -> None:
                self._payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        request = {
            "role": "support_lead",
            "action": "reply",
            "target_path": "artifacts/support_reply.provider.json",
            "reason": "Return JSON only.",
        }
        payload = {
            "message": {
                "content": json.dumps(
                    {
                        "reply_text": "收到，我先把这轮目标整理出来。",
                        "next_question": "",
                        "actions": [],
                        "debug_notes": "",
                    },
                    ensure_ascii=False,
                )
            }
        }

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            with mock.patch.object(
                ollama_agent,
                "_ensure_ollama_ready",
                return_value=(True, ""),
            ) as ensure_ready, mock.patch.object(
                ollama_agent.api_agent, "execute"
            ) as api_execute, mock.patch(
                "tools.providers.ollama_agent.urllib.request.urlopen",
                return_value=_Response(payload),
            ) as urlopen:
                out = ollama_agent.execute(
                    repo_root=ROOT,
                    run_dir=run_dir,
                    request=request,
                    config={},
                    guardrails_budgets={},
                )

            self.assertEqual(out.get("status"), "executed", msg=str(out))
            self.assertTrue((run_dir / "artifacts" / "support_reply.provider.json").exists())
            saved = json.loads((run_dir / "artifacts" / "support_reply.provider.json").read_text(encoding="utf-8"))
            self.assertEqual(str(saved.get("reply_text", "")), "收到，我先把这轮目标整理出来。")
            ensure_ready.assert_called_once()
            api_execute.assert_not_called()
            urlopen.assert_called_once()

    def test_execute_librarian_context_pack_uses_native_chat_api(self) -> None:
        class _Response:
            def __init__(self, payload: dict[str, object]) -> None:
                self._payload = json.dumps(payload, ensure_ascii=False).encode("utf-8")

            def read(self) -> bytes:
                return self._payload

            def __enter__(self) -> "_Response":
                return self

            def __exit__(self, exc_type, exc, tb) -> None:
                return None

        request = {
            "role": "librarian",
            "action": "context_pack",
            "target_path": "artifacts/context_pack.json",
            "reason": "Return JSON only.",
            "goal": "local librarian context pack",
        }
        payload = {
            "message": {
                "content": json.dumps(
                    {
                        "schema_version": "ctcp-context-pack-v1",
                        "goal": "local librarian context pack",
                        "repo_slug": "ctcp",
                        "summary": "included=1 omitted=0",
                        "files": [{"path": "README.md", "why": "local_model", "content": "sample"}],
                        "omitted": [],
                    },
                    ensure_ascii=False,
                )
            }
        }

        with tempfile.TemporaryDirectory() as td:
            run_dir = Path(td)
            (run_dir / "artifacts").mkdir(parents=True, exist_ok=True)
            (run_dir / "artifacts" / "file_request.json").write_text(
                json.dumps(
                    {
                        "schema_version": "ctcp-file-request-v1",
                        "goal": "local librarian context pack",
                        "needs": [{"path": "README.md", "mode": "snippets", "line_ranges": [[1, 20]]}],
                        "budget": {"max_files": 8, "max_total_bytes": 200000},
                        "reason": "test local librarian path",
                    },
                    ensure_ascii=False,
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
            with mock.patch.object(
                ollama_agent,
                "_ensure_ollama_ready",
                return_value=(True, ""),
            ) as ensure_ready, mock.patch.object(
                ollama_agent.api_agent, "execute"
            ) as api_execute, mock.patch(
                "tools.providers.ollama_agent.urllib.request.urlopen",
                return_value=_Response(payload),
            ) as urlopen:
                out = ollama_agent.execute(
                    repo_root=ROOT,
                    run_dir=run_dir,
                    request=request,
                    config={},
                    guardrails_budgets={},
                )

            self.assertEqual(out.get("status"), "executed", msg=str(out))
            self.assertEqual(out.get("provider_mode"), "local")
            self.assertEqual(out.get("fallback_blocked"), True)
            self.assertTrue(str(out.get("model_name", "")).strip())
            saved = json.loads((run_dir / "artifacts" / "context_pack.json").read_text(encoding="utf-8"))
            self.assertEqual(saved.get("schema_version"), "ctcp-context-pack-v1")
            self.assertTrue((run_dir / "outbox" / "AGENT_PROMPT_librarian_context_pack.md").exists())
            ensure_ready.assert_called_once()
            api_execute.assert_not_called()
            urlopen.assert_called_once()


if __name__ == "__main__":
    unittest.main()
