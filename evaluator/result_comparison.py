from __future__ import annotations

import argparse
import json
from collections.abc import Mapping
from pathlib import Path


METRIC_KEYS = (
    "hit_rate_at_10",
    "mrr",
    "mttc",
    "efficiency",
    "recommended_technical_score",
)


def _session_map(result: Mapping[str, object], label: str) -> dict[str, dict]:
    sessions = result.get("sessions")
    if not isinstance(sessions, list):
        raise ValueError(f"{label} result must contain a sessions list")
    mapped: dict[str, dict] = {}
    for index, session in enumerate(sessions):
        if not isinstance(session, dict):
            raise ValueError(f"{label} session {index} must be an object")
        sample_id = session.get("sample_id")
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError(f"{label} session {index} must have a sample_id")
        if sample_id in mapped:
            raise ValueError(f"{label} result contains duplicate session ID {sample_id}")
        if not isinstance(session.get("scenario_type"), str):
            raise ValueError(f"{label} session {sample_id} must have a scenario_type")
        if not isinstance(session.get("hit"), bool):
            raise ValueError(f"{label} session {sample_id} must have a boolean hit value")
        if session["hit"]:
            best_rank = session.get("best_rank")
            first_hit_turn = session.get("first_hit_turn")
            if isinstance(best_rank, bool) or not isinstance(best_rank, int) or not 1 <= best_rank <= 10:
                raise ValueError(f"{label} hit session {sample_id} must have a best_rank from 1 to 10")
            if (
                isinstance(first_hit_turn, bool)
                or not isinstance(first_hit_turn, int)
                or not 1 <= first_hit_turn <= 10
            ):
                raise ValueError(
                    f"{label} hit session {sample_id} must have a first_hit_turn from 1 to 10"
                )
        elif session.get("best_rank") is not None or session.get("first_hit_turn") is not None:
            raise ValueError(
                f"{label} miss session {sample_id} must have null best_rank and first_hit_turn"
            )
        mapped[sample_id] = session
    return mapped


def _validate_metrics(result: Mapping[str, object], label: str) -> None:
    for key in METRIC_KEYS:
        value = result.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError(f"{label} result must contain numeric metric {key}")


def _metric_deltas(
    baseline: Mapping[str, object],
    candidate: Mapping[str, object],
) -> dict[str, float]:
    deltas: dict[str, float] = {}
    for key in METRIC_KEYS:
        deltas[key] = round(float(candidate[key]) - float(baseline[key]), 6)
    return deltas


def compare_results(
    baseline: Mapping[str, object],
    candidate: Mapping[str, object],
) -> dict:
    _validate_metrics(baseline, "baseline")
    _validate_metrics(candidate, "candidate")
    baseline_sessions = _session_map(baseline, "baseline")
    candidate_sessions = _session_map(candidate, "candidate")
    if baseline_sessions.keys() != candidate_sessions.keys():
        raise ValueError("baseline and candidate must contain the same session IDs")

    fixed: list[str] = []
    broken: list[str] = []
    rank_improved: list[str] = []
    rank_regressed: list[str] = []
    turn_improved: list[str] = []
    turn_regressed: list[str] = []
    scenarios: dict[str, dict[str, list[str]]] = {}

    for sample_id in sorted(baseline_sessions):
        before = baseline_sessions[sample_id]
        after = candidate_sessions[sample_id]
        scenario = str(before["scenario_type"])
        if after["scenario_type"] != scenario:
            raise ValueError(f"scenario_type changed for session {sample_id}")
        changes = scenarios.setdefault(
            scenario,
            {"fixed_session_ids": [], "broken_session_ids": []},
        )
        if not before["hit"] and after["hit"]:
            fixed.append(sample_id)
            changes["fixed_session_ids"].append(sample_id)
            continue
        if before["hit"] and not after["hit"]:
            broken.append(sample_id)
            changes["broken_session_ids"].append(sample_id)
            continue
        if not before["hit"]:
            continue

        before_rank = before.get("best_rank")
        after_rank = after.get("best_rank")
        if isinstance(before_rank, int) and isinstance(after_rank, int):
            if after_rank < before_rank:
                rank_improved.append(sample_id)
            elif after_rank > before_rank:
                rank_regressed.append(sample_id)

        before_turn = before.get("first_hit_turn")
        after_turn = after.get("first_hit_turn")
        if isinstance(before_turn, int) and isinstance(after_turn, int):
            if after_turn < before_turn:
                turn_improved.append(sample_id)
            elif after_turn > before_turn:
                turn_regressed.append(sample_id)

    return {
        "baseline_sample_count": len(baseline_sessions),
        "candidate_sample_count": len(candidate_sessions),
        "metric_deltas": _metric_deltas(baseline, candidate),
        "fixed_session_ids": fixed,
        "broken_session_ids": broken,
        "rank_improved_session_ids": rank_improved,
        "rank_regressed_session_ids": rank_regressed,
        "turn_improved_session_ids": turn_improved,
        "turn_regressed_session_ids": turn_regressed,
        "scenario_changes": {name: scenarios[name] for name in sorted(scenarios)},
    }


def load_result(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"result file must contain a JSON object: {path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare two TechJam evaluation results")
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()

    comparison = compare_results(load_result(args.baseline), load_result(args.candidate))
    rendered = json.dumps(comparison, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
