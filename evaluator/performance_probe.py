from __future__ import annotations

import argparse
import json
import platform
import sqlite3
import time
from pathlib import Path

from evaluator.local_evaluator import catalog_index, evaluate, load_jsonl
from starter.agent import Agent


def percentile(values: list[float], proportion: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    position = (len(ordered) - 1) * proportion
    lower = int(position)
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + fraction * (ordered[upper] - ordered[lower])


class TimedAgent:
    def __init__(self, agent: Agent) -> None:
        self.agent = agent
        self.response_seconds: list[float] = []

    def reset(self, session_id: str, user_profile: dict) -> None:
        self.agent.reset(session_id, user_profile)

    def respond(
        self,
        session_id: str,
        user_message: str,
        turn: int,
        top_k: int,
    ) -> dict:
        started = time.perf_counter()
        response = self.agent.respond(session_id, user_message, turn, top_k)
        self.response_seconds.append(time.perf_counter() - started)
        return response


def main() -> None:
    parser = argparse.ArgumentParser(description="Measure local Agent latency and cost evidence")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--dataset", default="data/public_set.jsonl")
    parser.add_argument("--output")
    args = parser.parse_args()

    samples = load_jsonl(args.dataset)
    catalog_ids, categories, products = catalog_index(args.catalog)

    index_started = time.perf_counter()
    timed_agent = TimedAgent(Agent(args.catalog))
    index_build_seconds = time.perf_counter() - index_started

    evaluation_started = time.perf_counter()
    result = evaluate(timed_agent, samples, catalog_ids, categories, products)
    evaluation_seconds = time.perf_counter() - evaluation_started
    response_ms = [duration * 1000.0 for duration in timed_agent.response_seconds]

    evidence = {
        "python_version": platform.python_version(),
        "sqlite_version": sqlite3.sqlite_version,
        "sample_count": result["sample_count"],
        "index_build_seconds": round(index_build_seconds, 6),
        "evaluation_seconds_excluding_index_build": round(evaluation_seconds, 6),
        "response_count": len(response_ms),
        "response_latency_ms": {
            "p50": round(percentile(response_ms, 0.50), 6),
            "p95": round(percentile(response_ms, 0.95), 6),
            "maximum": round(max(response_ms, default=0.0), 6),
        },
        "reported_token_usage": result["reported_token_usage"],
        "estimated_api_cost_usd": 0.0,
        "network_required_during_inference": False,
        "technical_score": result["recommended_technical_score"],
    }
    rendered = json.dumps(evidence, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    print(rendered, end="")


if __name__ == "__main__":
    main()
