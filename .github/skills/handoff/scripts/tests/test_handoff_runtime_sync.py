from __future__ import annotations

import subprocess
from pathlib import Path
import tempfile
import unittest


def _repo_root() -> Path:
    current = Path(__file__).resolve()
    for candidate in (current, *current.parents):
        if (candidate / ".github").exists():
            return candidate
    raise RuntimeError("Could not locate repository root from test location")


ROOT = _repo_root()
SYNC_SCRIPT = ROOT / ".github" / "skills" / "handoff" / "scripts" / "handoff-runtime-sync.sh"


class TestHandoffRuntimeSync(unittest.TestCase):
    def test_handoff_runtime_sync_copies_and_cleans_schema_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            repo_root = tmp_path / "repo"
            source = repo_root / ".github" / "handoffs"
            source.mkdir(parents=True)

            (source / "WORK_HANDOFF.schema.yaml").write_text(
                "layer: test\nschema: work_handoff_v1\n", encoding="utf-8"
            )
            (source / "EXPERT_REQUEST.schema.yaml").write_text(
                "layer: test\nschema: expert_request_v1\n", encoding="utf-8"
            )

            runtime_dir = repo_root / ".digital-runtime" / "layers" / "test-layer" / "handoffs"
            runtime_dir.mkdir(parents=True)
            (runtime_dir / "STALE.schema.yaml").write_text(
                "schema: stale_v1\n", encoding="utf-8"
            )

            result = subprocess.run(
                [
                    "bash",
                    str(SYNC_SCRIPT),
                    "--repo-root",
                    str(repo_root),
                    "--layer",
                    "test-layer",
                ],
                text=True,
                capture_output=True,
                check=False,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue((runtime_dir / "WORK_HANDOFF.schema.yaml").exists())
            self.assertTrue((runtime_dir / "EXPERT_REQUEST.schema.yaml").exists())
            self.assertFalse((runtime_dir / "STALE.schema.yaml").exists())

            index_file = runtime_dir / "handoff-index.tsv"
            self.assertTrue(index_file.exists())
            index_content = index_file.read_text(encoding="utf-8")
            self.assertIn("schema\tfile\tsha256", index_content)
            self.assertIn("work_handoff_v1", index_content)
            self.assertIn("expert_request_v1", index_content)


if __name__ == "__main__":
    unittest.main()
