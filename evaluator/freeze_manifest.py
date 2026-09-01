from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections.abc import Iterable
from pathlib import Path


DEFAULT_RUNTIME_PATHS = (
    "starter/agent.py",
    "evaluator/local_evaluator.py",
    "evaluator/result_comparison.py",
    "evaluator/performance_probe.py",
    "evaluator/freeze_manifest.py",
    "demo.py",
)
METRIC_KEYS = (
    "hit_rate_at_10",
    "mrr",
    "mttc",
    "efficiency",
    "recommended_technical_score",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_manifest(
    root: str | Path,
    result_path: str | Path,
    runtime_paths: Iterable[str] = DEFAULT_RUNTIME_PATHS,
) -> dict:
    project_root = Path(root).resolve()
    result_file = Path(result_path).resolve()
    result = json.loads(result_file.read_text(encoding="utf-8"))
    if not isinstance(result, dict):
        raise ValueError("result file must contain a JSON object")
    sample_count = result.get("sample_count")
    if isinstance(sample_count, bool) or not isinstance(sample_count, int):
        raise ValueError("result file must contain an integer sample_count")

    normalized_paths = sorted({str(Path(path)) for path in runtime_paths})
    if not normalized_paths:
        raise ValueError("at least one runtime file is required")
    runtime_files: dict[str, str] = {}
    for relative_path in normalized_paths:
        supplied_path = Path(relative_path)
        if supplied_path.is_absolute():
            raise ValueError(f"runtime path must be relative: {relative_path}")
        candidate = (project_root / supplied_path).resolve()
        if not candidate.is_relative_to(project_root):
            raise ValueError(f"runtime path leaves the project root: {relative_path}")
        if not candidate.is_file():
            raise FileNotFoundError(f"runtime file is missing: {relative_path}")
        runtime_files[relative_path] = _sha256(candidate)

    tree_digest = hashlib.sha256()
    for relative_path, file_digest in runtime_files.items():
        tree_digest.update(relative_path.encode("utf-8"))
        tree_digest.update(b"\0")
        tree_digest.update(file_digest.encode("ascii"))
        tree_digest.update(b"\n")

    missing_metrics = [key for key in METRIC_KEYS if key not in result]
    if missing_metrics:
        raise ValueError("result file is missing metrics: " + ", ".join(missing_metrics))
    metrics: dict[str, int | float] = {}
    for key in METRIC_KEYS:
        value = result[key]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(float(value))
        ):
            raise ValueError(f"result metric must be a finite number: {key}")
        metrics[key] = value
    return {
        "schema_version": 1,
        "sample_count": sample_count,
        "metrics": metrics,
        "runtime_tree_sha256": tree_digest.hexdigest(),
        "runtime_files": runtime_files,
        "result_sha256": _sha256(result_file),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Create an aggregate-only freeze receipt for the Agent and a full result file"
    )
    parser.add_argument("--root", default=".")
    parser.add_argument("--result", required=True)
    parser.add_argument("--output", default="results/freeze-manifest.json")
    args = parser.parse_args()

    manifest = build_manifest(args.root, args.result)
    rendered = json.dumps(manifest, indent=2) + "\n"
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
