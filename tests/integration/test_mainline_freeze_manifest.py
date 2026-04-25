from __future__ import annotations

import hashlib
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "artifacts" / "mainline_freeze_manifest.json"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class MainlineFreezeManifestTests(unittest.TestCase):
    def test_protected_mainline_files_match_freeze_manifest(self) -> None:
        self.assertTrue(MANIFEST.exists(), f"missing freeze manifest: {MANIFEST}")
        manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
        protected_files = manifest.get("protected_files", [])
        self.assertTrue(protected_files, "mainline freeze manifest has no protected_files")

        for entry in protected_files:
            rel_path = entry.get("path", "")
            expected = entry.get("sha256", "")
            self.assertTrue(rel_path, "freeze manifest entry missing path")
            self.assertTrue(expected, f"freeze manifest entry missing sha256: {rel_path}")
            target = ROOT / rel_path
            self.assertTrue(target.exists(), f"protected mainline file missing: {rel_path}")
            actual = _sha256(target)
            self.assertEqual(
                expected,
                actual,
                f"protected mainline file changed: {rel_path}",
            )


if __name__ == "__main__":
    unittest.main()

