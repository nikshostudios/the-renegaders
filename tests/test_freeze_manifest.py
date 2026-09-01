from __future__ import annotations

import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from evaluator.freeze_manifest import build_manifest


class FreezeManifestTest(unittest.TestCase):
    @staticmethod
    def _write_result(path: Path, **overrides: object) -> None:
        payload = {
            "sample_count": 2,
            "hit_rate_at_10": 0.5,
            "mrr": 0.25,
            "mttc": 6.0,
            "efficiency": 0.5,
            "recommended_technical_score": 0.4,
            "sessions": [{"sample_id": "private-example"}],
        }
        payload.update(overrides)
        path.write_text(json.dumps(payload) + "\n", encoding="utf-8")

    def test_manifest_hashes_runtime_files_and_full_result_without_paths(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "starter").mkdir()
            (root / "starter" / "agent.py").write_text("print('agent')\n", encoding="utf-8")
            result = root / "private-result.json"
            self._write_result(result)

            manifest = build_manifest(
                root,
                result,
                runtime_paths=("starter/agent.py",),
            )
            expected_result_hash = hashlib.sha256(result.read_bytes()).hexdigest()

        rendered = json.dumps(manifest, sort_keys=True)
        self.assertEqual(
            set(manifest),
            {
                "schema_version",
                "sample_count",
                "metrics",
                "runtime_tree_sha256",
                "runtime_files",
                "result_sha256",
            },
        )
        self.assertEqual(manifest["result_sha256"], expected_result_hash)
        self.assertEqual(manifest["sample_count"], 2)
        self.assertEqual(list(manifest["runtime_files"]), ["starter/agent.py"])
        self.assertTrue(
            all(
                isinstance(value, (int, float)) and not isinstance(value, bool)
                for value in manifest["metrics"].values()
            )
        )
        self.assertNotIn("private-example", rendered)
        self.assertNotIn(directory, rendered)

    def test_rejects_missing_or_non_numeric_metrics(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            runtime = root / "agent.py"
            runtime.write_text("agent\n", encoding="utf-8")
            result = root / "result.json"
            self._write_result(result)
            payload = json.loads(result.read_text(encoding="utf-8"))
            del payload["recommended_technical_score"]
            result.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(ValueError):
                build_manifest(root, result, runtime_paths=("agent.py",))

            self._write_result(result, mrr={"per_session": [1, 2]})
            with self.assertRaises(ValueError):
                build_manifest(root, result, runtime_paths=("agent.py",))

    def test_runtime_tree_hash_tracks_bytes_not_input_order(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "a.py").write_text("a\n", encoding="utf-8")
            (root / "b.py").write_text("b\n", encoding="utf-8")
            result = root / "result.json"
            self._write_result(result)
            first = build_manifest(root, result, runtime_paths=("b.py", "a.py"))
            reordered = build_manifest(root, result, runtime_paths=("a.py", "b.py"))
            self.assertEqual(first["runtime_tree_sha256"], reordered["runtime_tree_sha256"])

            (root / "a.py").write_text("changed\n", encoding="utf-8")
            changed = build_manifest(root, result, runtime_paths=("a.py", "b.py"))
            self.assertNotEqual(first["runtime_tree_sha256"], changed["runtime_tree_sha256"])

    def test_rejects_runtime_paths_outside_the_project(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "agent.py").write_text("agent\n", encoding="utf-8")
            result = root / "result.json"
            self._write_result(result)
            with self.assertRaises(ValueError):
                build_manifest(root, result, runtime_paths=("/etc/hosts",))
            with self.assertRaises(ValueError):
                build_manifest(root, result, runtime_paths=("../outside.py",))


if __name__ == "__main__":
    unittest.main()
