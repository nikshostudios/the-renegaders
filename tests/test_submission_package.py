from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BUNDLE = PROJECT_ROOT / "submission"
FROZEN_RUNTIME = PROJECT_ROOT / "starter" / "agent.py"

EXPECTED_BUNDLE_FILES = {
    "README.md",
    "REPORT.md",
    "agent.py",
    "requirements.txt",
}

ALLOWED_ATTRIBUTES = {
    "category", "material", "color", "size", "style", "brand",
    "budget", "feature", "use_case", "other",
}

SECRET_PATTERNS = (
    r"sk-[A-Za-z0-9]{20,}",
    r"ghp_[A-Za-z0-9]{30,}",
    r"github_pat_[A-Za-z0-9_]{50,}",
    r"AKIA[0-9A-Z]{16}",
    r"AIza[0-9A-Za-z_\-]{30,}",
    r"xox[baprs]-",
    r"BEGIN [A-Z ]*PRIVATE KEY",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _bundle_files() -> list[Path]:
    return sorted(path for path in BUNDLE.rglob("*") if path.is_file())


def _synthetic_catalog(directory: Path) -> Path:
    products = [
        {
            "parent_asin": "SYN0000001",
            "title": "Black leather wallet",
            "categories": ["Accessories", "Wallets"],
            "features": ["genuine leather", "slim profile"],
            "details": {"Closure": "snap"},
            "store": "SynthStore",
            "description": "A compact black leather wallet.",
        },
        {
            "parent_asin": "SYN0000002",
            "title": "Blue cotton running shoe",
            "categories": ["Shoes", "Athletic"],
            "features": ["breathable cotton upper"],
            "details": {"Sole": "rubber"},
            "store": "SynthStore",
            "description": "A lightweight blue running shoe.",
        },
        {
            "parent_asin": "SYN0000003",
            "title": "Wool winter jacket",
            "categories": ["Clothing", "Jackets"],
            "features": ["wool blend", "waterproof shell"],
            "details": {"Fit": "regular"},
            "store": "SynthStore",
            "description": "A warm wool winter jacket.",
        },
    ]
    catalog = directory / "synthetic_catalog.jsonl"
    catalog.write_text(
        "".join(json.dumps(product) + "\n" for product in products),
        encoding="utf-8",
    )
    return catalog


class SubmissionBundleContentsTest(unittest.TestCase):
    def test_bundle_directory_exists(self) -> None:
        self.assertTrue(BUNDLE.is_dir(), "submission/ bundle directory is missing")

    def test_agent_is_byte_identical_to_the_frozen_runtime(self) -> None:
        submitted = BUNDLE / "agent.py"
        self.assertTrue(submitted.is_file(), "submission/agent.py is missing")
        self.assertEqual(
            _sha256(submitted),
            _sha256(FROZEN_RUNTIME),
            "submission/agent.py must be byte-identical to the frozen starter/agent.py",
        )

    def test_bundle_contains_only_the_expected_files(self) -> None:
        relative = {
            str(path.relative_to(BUNDLE))
            for path in _bundle_files()
            if "__pycache__" not in path.parts
        }
        self.assertEqual(relative, EXPECTED_BUNDLE_FILES)

    def test_requirements_declares_no_third_party_dependency(self) -> None:
        lines = (BUNDLE / "requirements.txt").read_text(encoding="utf-8").splitlines()
        requirements = [
            line.strip() for line in lines
            if line.strip() and not line.strip().startswith("#")
        ]
        self.assertEqual(requirements, [])

    def test_agent_module_imports_only_the_standard_library(self) -> None:
        source = (BUNDLE / "agent.py").read_text(encoding="utf-8")
        imported_roots = set()
        for match in re.finditer(r"^\s*(?:from|import)\s+([A-Za-z_][\w.]*)", source, re.M):
            imported_roots.add(match.group(1).split(".")[0])
        self.assertTrue(imported_roots, "expected at least one import")
        # sys.stdlib_module_names exists from Python 3.10. Fall back to an explicit
        # allowlist so this check still runs on an older interpreter.
        stdlib = set(getattr(sys, "stdlib_module_names", ())) or {
            "__future__", "json", "re", "sqlite3", "pathlib", "typing",
            "argparse", "hashlib", "math", "collections", "dataclasses",
        }
        unexpected = imported_roots - stdlib
        self.assertEqual(unexpected, set(), f"non-standard-library imports: {sorted(unexpected)}")
        for forbidden in ("starter", "evaluator", "tests", "demo", "submission"):
            self.assertNotIn(forbidden, imported_roots)

    def test_readme_documents_python_version_network_and_run_command(self) -> None:
        readme = (BUNDLE / "README.md").read_text(encoding="utf-8").lower()
        self.assertIn("python 3.10", readme)
        self.assertIn("network", readme)
        self.assertIn("data/catalog.jsonl", readme)

    def test_report_documents_cost_latency_and_limitations(self) -> None:
        report = (BUNDLE / "REPORT.md").read_text(encoding="utf-8").lower()
        for required in ("limitation", "latency", "token", "cost"):
            self.assertIn(required, report)


class SubmissionBundleSafetyTest(unittest.TestCase):
    def _bundle_text(self) -> dict[str, str]:
        return {
            str(path.relative_to(BUNDLE)): path.read_text(encoding="utf-8", errors="replace")
            for path in _bundle_files()
            if "__pycache__" not in path.parts
        }

    def test_bundle_contains_no_secret_material(self) -> None:
        for name, text in self._bundle_text().items():
            for pattern in SECRET_PATTERNS:
                self.assertIsNone(
                    re.search(pattern, text),
                    f"{name} matched a secret pattern",
                )

    def test_bundle_contains_no_machine_local_absolute_paths(self) -> None:
        for name, text in self._bundle_text().items():
            self.assertNotIn("/Users/", text, f"{name} contains a machine-local path")
            self.assertNotIn("/home/", text, f"{name} contains a machine-local path")
            self.assertNotIn("C:\\Users", text, f"{name} contains a machine-local path")

    def test_bundle_contains_no_catalog_or_dataset_records(self) -> None:
        for path in _bundle_files():
            self.assertNotIn(
                path.suffix,
                {".jsonl", ".gz", ".zip", ".ipynb", ".csv", ".parquet", ".env"},
                f"{path.name} is a data or archive artifact",
            )

    def test_bundle_contains_no_public_set_target_identifiers(self) -> None:
        public_set = PROJECT_ROOT / "data" / "public_set.jsonl"
        if not public_set.is_file():
            self.skipTest("public_set.jsonl is unavailable")
        targets = set()
        with public_set.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                sample = json.loads(line)
                target = sample.get("ground_truth", {}).get("parent_asin")
                if target:
                    targets.add(str(target))
        self.assertTrue(targets, "expected at least one public-set target identifier")
        leaked = 0
        for text in self._bundle_text().values():
            leaked += sum(1 for target in targets if target in text)
        self.assertEqual(leaked, 0, "bundle leaks public-set target identifiers")


class SubmissionCleanRoomTest(unittest.TestCase):
    def test_extracted_bundle_runs_a_protocol_valid_session_without_the_repository(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = Path(directory)
            extracted = workspace / "extracted"
            shutil.copytree(BUNDLE, extracted, ignore=shutil.ignore_patterns("__pycache__"))
            catalog = _synthetic_catalog(workspace)

            driver = extracted / "clean_room_driver.py"
            driver.write_text(
                "import json, sys\n"
                "from agent import Agent\n"
                "agent = Agent(sys.argv[1])\n"
                "agent.reset('clean-room', {\n"
                "    'purchase_frequency': 'low',\n"
                "    'average_prior_rating': 4.2,\n"
                "    'rating_style': 'generous',\n"
                "    'preference_tags': ['leather'],\n"
                "    'summary': 'Occasional accessory buyer.',\n"
                "})\n"
                "turns = [\n"
                "    'I am looking for wallets, but I am still exploring.',\n"
                "    'For that, what matters is: leather; color: black.',\n"
                "    'Actually, ignore my earlier preference. What I need is: wool jacket.',\n"
                "]\n"
                "out = [agent.respond('clean-room', message, index, 10)\n"
                "       for index, message in enumerate(turns, start=1)]\n"
                "print(json.dumps(out))\n",
                encoding="utf-8",
            )

            environment = {
                key: value for key, value in os.environ.items()
                if key not in {"PYTHONPATH", "PYTHONHOME", "PYTHONSTARTUP"}
            }
            completed = subprocess.run(
                [sys.executable, "clean_room_driver.py", str(catalog)],
                cwd=str(extracted),
                env=environment,
                capture_output=True,
                text=True,
                timeout=120,
            )

        self.assertEqual(
            completed.returncode,
            0,
            f"clean-room run failed: {completed.stderr[-2000:]}",
        )
        responses = json.loads(completed.stdout)
        self.assertEqual(len(responses), 3)
        for turn, response in enumerate(responses, start=1):
            self.assertIsInstance(response, dict)
            self.assertEqual(
                set(response) <= {"message", "ask_attribute", "recommendations", "usage"},
                True,
                "response contains fields outside the agent contract",
            )
            self.assertIsInstance(response["message"], str)
            self.assertTrue(response["message"].strip())
            attribute = response["ask_attribute"]
            self.assertTrue(attribute is None or attribute in ALLOWED_ATTRIBUTES)
            recommendations = response["recommendations"]
            self.assertIsInstance(recommendations, list)
            self.assertLessEqual(len(recommendations), 10)
            identifiers = []
            for item in recommendations:
                self.assertIsInstance(item, dict)
                self.assertTrue(set(item) <= {"parent_asin", "score"})
                self.assertIsInstance(item["parent_asin"], str)
                self.assertTrue(item["parent_asin"])
                identifiers.append(item["parent_asin"])
            self.assertEqual(len(identifiers), len(set(identifiers)), "duplicate parent_asin")
            usage = response["usage"]
            self.assertIsInstance(usage["prompt_tokens"], int)
            self.assertIsInstance(usage["completion_tokens"], int)
            self.assertGreaterEqual(usage["prompt_tokens"], 0)
            self.assertGreaterEqual(usage["completion_tokens"], 0)
            self.assertTrue(identifiers, f"turn {turn} returned no recommendations")


if __name__ == "__main__":
    unittest.main()
