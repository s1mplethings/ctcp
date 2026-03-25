from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import scripts.ctcp_persona_lab as persona_lab


class PersonaLabRunnerTests(unittest.TestCase):
    def test_run_fixture_suite_writes_pass_artifacts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_persona_lab_pass_") as td:
            run_dir = Path(td) / "persona-pass"
            with mock.patch.object(persona_lab.reference_export, "current_source_commit", return_value="deadbeef"):
                out_dir, manifest = persona_lab.run_fixture_suite(
                    case_fixtures={
                        "no_mechanical_greeting": [
                            "问题是当前任务缺少一个明确判断锚点。下一步我先列出最小修改方案。"
                        ]
                    },
                    case_ids=["no_mechanical_greeting"],
                    raw_run_dir=str(run_dir),
                )

            self.assertEqual(out_dir, run_dir.resolve())
            self.assertEqual(manifest["fail_count"], 0)
            self.assertTrue((run_dir / "manifest.json").exists())
            self.assertTrue((run_dir / "summary.md").exists())
            case_dir = run_dir / "cases" / "no_mechanical_greeting"
            for name in ("transcript.md", "transcript.json", "score.json", "fail_reasons.md", "summary.md"):
                self.assertTrue((case_dir / name).exists(), msg=name)
            score_doc = json.loads((case_dir / "score.json").read_text(encoding="utf-8"))
            self.assertEqual(score_doc["verdict"], "pass")
            self.assertEqual(score_doc["source_commit"], "deadbeef")
            transcript_doc = json.loads((case_dir / "transcript.json").read_text(encoding="utf-8"))
            self.assertTrue(str(transcript_doc["session_id"]).startswith("no_mechanical_greeting-"))

    def test_run_fixture_suite_fails_on_mechanical_reply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_persona_lab_fail_") as td:
            run_dir = Path(td) / "persona-fail"
            with mock.patch.object(persona_lab.reference_export, "current_source_commit", return_value="deadbeef"):
                _, manifest = persona_lab.run_fixture_suite(
                    case_fixtures={"no_mechanical_greeting": ["收到，我先帮你整理一下。"]},
                    case_ids=["no_mechanical_greeting"],
                    raw_run_dir=str(run_dir),
                )

            self.assertEqual(manifest["fail_count"], 1)
            score_doc = json.loads((run_dir / "cases" / "no_mechanical_greeting" / "score.json").read_text(encoding="utf-8"))
            self.assertEqual(score_doc["verdict"], "fail")
            self.assertIn("response_style_lint.first_sentence_direct", score_doc["fail_reason_ids"])
            self.assertIn("response_style_lint.banned_phrase", score_doc["fail_reason_ids"])
            fail_md = (run_dir / "cases" / "no_mechanical_greeting" / "fail_reasons.md").read_text(encoding="utf-8")
            self.assertIn("banned_phrase_hit", fail_md)

    def test_run_fixture_suite_fails_on_low_information_ack_reply(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_persona_lab_low_info_fail_") as td:
            run_dir = Path(td) / "persona-low-info-fail"
            with mock.patch.object(persona_lab.reference_export, "current_source_commit", return_value="deadbeef"):
                _, manifest = persona_lab.run_fixture_suite(
                    case_fixtures={"no_mechanical_greeting": ["好的，我在处理。"]},
                    case_ids=["no_mechanical_greeting"],
                    raw_run_dir=str(run_dir),
                )

            self.assertEqual(manifest["fail_count"], 1)
            score_doc = json.loads((run_dir / "cases" / "no_mechanical_greeting" / "score.json").read_text(encoding="utf-8"))
            self.assertEqual(score_doc["verdict"], "fail")
            self.assertIn("response_style_lint.first_sentence_direct", score_doc["fail_reason_ids"])
            self.assertIn("response_style_lint.status_anchor_present", score_doc["fail_reason_ids"])

    def test_run_fixture_suite_passes_status_transition_reaction_case(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_persona_lab_transition_pass_") as td:
            run_dir = Path(td) / "persona-transition-pass"
            with mock.patch.object(persona_lab.reference_export, "current_source_commit", return_value="deadbeef"):
                _, manifest = persona_lab.run_fixture_suite(
                    case_fixtures={
                        "status_transition_reaction": [
                            "当前判断是流程已从澄清阶段进入执行阶段，原因是需求确认完成。我现在先落地规则补丁，下一步由我跑验证并回传结果。"
                        ]
                    },
                    case_ids=["status_transition_reaction"],
                    raw_run_dir=str(run_dir),
                )

            self.assertEqual(manifest["fail_count"], 0)
            score_doc = json.loads((run_dir / "cases" / "status_transition_reaction" / "score.json").read_text(encoding="utf-8"))
            self.assertEqual(score_doc["verdict"], "pass")
            self.assertNotIn("response_style_lint.transition_response_complete", score_doc["fail_reason_ids"])

    def test_run_fixture_suite_uses_fresh_session_per_case(self) -> None:
        with tempfile.TemporaryDirectory(prefix="ctcp_persona_lab_isolation_") as td:
            run_dir = Path(td) / "persona-isolation"
            with mock.patch.object(persona_lab.reference_export, "current_source_commit", return_value="deadbeef"):
                _, manifest = persona_lab.run_fixture_suite(
                    case_fixtures={
                        "no_empty_clarification": [
                            "判断：任务已经明确。下一步我先列出文档入口和最小改动步骤。"
                        ],
                        "multi_turn_no_reset": [
                            "判断：上下文已经建立。下一步我先继续当前结论。",
                            "判断：方向没变。下一步我把当前动作接上。",
                            "判断：不需要重启开场。下一步我继续给出当前动作。",
                        ],
                    },
                    case_ids=["no_empty_clarification", "multi_turn_no_reset"],
                    raw_run_dir=str(run_dir),
                )

            fresh = manifest["fresh_session_evidence"]
            self.assertTrue(fresh["unique_session_ids"])
            self.assertEqual(len(fresh["session_ids"]), 2)
            self.assertEqual(len(set(fresh["session_ids"])), 2)
            transcript_a = json.loads((run_dir / "cases" / "no_empty_clarification" / "transcript.json").read_text(encoding="utf-8"))
            transcript_b = json.loads((run_dir / "cases" / "multi_turn_no_reset" / "transcript.json").read_text(encoding="utf-8"))
            self.assertNotEqual(transcript_a["session_id"], transcript_b["session_id"])
            self.assertEqual(transcript_b["stop_reason"], "fixture_replies_consumed")


if __name__ == "__main__":
    unittest.main()
