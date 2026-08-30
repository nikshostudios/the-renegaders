from __future__ import annotations

import argparse
import json
from pathlib import Path

from starter.agent import Agent


SCENARIOS = (
    (
        "Buying",
        (
            "I'm looking for walking shoes. A key requirement is leather.",
            "For that, what matters is: rubber sole.",
        ),
    ),
    (
        "Browsing",
        (
            "I'm looking for wallets, but I'm still exploring.",
            "For that, what matters is: leather; color: black.",
        ),
    ),
    (
        "Intent change",
        (
            "I'm looking for jackets. I prefer wool.",
            "Actually, ignore my earlier preference. What I need is: waterproof.",
        ),
    ),
)


def product_titles(catalog_path: str | Path) -> dict[str, str]:
    titles: dict[str, str] = {}
    with Path(catalog_path).open(encoding="utf-8") as handle:
        for line in handle:
            product = json.loads(line)
            titles[str(product["parent_asin"])] = str(product.get("title") or "Untitled product")
    return titles


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a deterministic multi-turn Agent demo")
    parser.add_argument("--catalog", default="data/catalog.jsonl")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    titles = product_titles(args.catalog)
    agent = Agent(args.catalog)
    for scenario_index, (scenario_name, messages) in enumerate(SCENARIOS, start=1):
        session_id = f"demo_{scenario_index}"
        agent.reset(session_id, {})
        print(f"\n## {scenario_name}")
        for turn, user_message in enumerate(messages, start=1):
            response = agent.respond(session_id, user_message, turn, args.top_k)
            print(f"\nCustomer: {user_message}")
            print(f"Agent: {response['message']}")
            print(f"Question attribute: {response['ask_attribute']}")
            for rank, recommendation in enumerate(response["recommendations"], start=1):
                parent_asin = str(recommendation["parent_asin"])
                print(f"{rank}. {titles.get(parent_asin, 'Unknown product')} ({parent_asin})")


if __name__ == "__main__":
    main()
