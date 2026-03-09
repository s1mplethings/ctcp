from __future__ import annotations

import json
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "triplet_guard" / "skill_consumption_cases.json"


def _has_runtime_evidence(repo_root: Path, evidence_paths: list[str], skill_name: str) -> bool:
    token = str(skill_name or "").strip().lower()
    for rel in evidence_paths:
        path = (repo_root / str(rel)).resolve()
        if not path.exists() or not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").lower()
        if token and token in text:
            return True
    return False


def _has_explicit_non_skill_reason(decision: str) -> bool:
    raw = str(decision or "").strip()
    low = raw.lower()
    if not re.search(r"skillized\s*:\s*no\b", low):
        return False
    return ("because" in low) or ("因为" in raw)


def _assert_skill_contract(repo_root: Path, case: dict) -> None:
    claims_usage = bool(case.get("claims_skill_usage", False))
    skill_name = str(case.get("skill_name", "")).strip()
    evidence_paths = [str(x) for x in case.get("runtime_evidence", []) if str(x).strip()]
    decision = str(case.get("decision", "")).strip()

    if claims_usage:
        if _has_runtime_evidence(repo_root, evidence_paths, skill_name):
            return
        raise AssertionError("skill usage is claimed but no runtime evidence was found")

    if _has_explicit_non_skill_reason(decision):
        return
    raise AssertionError("workflow is not skillized but missing explicit 'skillized: no, because ...' justification")


class SkillConsumptionContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.fixture = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

    def test_skill_directory_existence_alone_is_insufficient(self) -> None:
        skills_dir = ROOT / ".agents" / "skills"
        self.assertTrue(skills_dir.exists(), msg="expected .agents/skills to exist in repository")
        case = dict(self.fixture["usage_without_evidence"])
        with self.assertRaisesRegex(AssertionError, "no runtime evidence"):
            _assert_skill_contract(ROOT, case)

    def test_claimed_skill_usage_requires_runtime_evidence(self) -> None:
        with self.assertRaisesRegex(AssertionError, "no runtime evidence"):
            _assert_skill_contract(ROOT, dict(self.fixture["usage_without_evidence"]))
        _assert_skill_contract(ROOT, dict(self.fixture["usage_with_evidence"]))

    def test_non_skillized_workflow_requires_explicit_reason(self) -> None:
        _assert_skill_contract(ROOT, dict(self.fixture["not_skillized_with_reason"]))
        with self.assertRaisesRegex(AssertionError, "missing explicit"):
            _assert_skill_contract(ROOT, dict(self.fixture["not_skillized_without_reason"]))


if __name__ == "__main__":
    unittest.main()
