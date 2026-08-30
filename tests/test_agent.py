from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from starter.agent import Agent


class AgentConversationTest(unittest.TestCase):
    def test_equal_reranker_scores_preserve_lexical_order(self) -> None:
        products = [
            {
                "parent_asin": "FIRST",
                "title": "Red leather wallet",
                "categories": ["Accessories"],
            },
            {
                "parent_asin": "SECOND",
                "title": "Red leather wallet",
                "categories": ["Accessories"],
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.jsonl"
            catalog.write_text(
                "".join(json.dumps(product) + "\n" for product in products),
                encoding="utf-8",
            )
            agent = Agent(catalog)
            agent.reset("session", {})
            response = agent.respond(
                "session",
                "I'm looking for a red leather wallet.",
                1,
                2,
            )

        self.assertEqual(
            [item["parent_asin"] for item in response["recommendations"]],
            ["FIRST", "SECOND"],
        )

    def test_reranker_promotes_broader_field_coverage_from_deeper_pool(self) -> None:
        products = [
            {
                "parent_asin": f"DISTRACTOR_{index:02d}",
                "title": "Wallet leather",
                "categories": ["Accessories"],
            }
            for index in range(11)
        ]
        products.append({
            "parent_asin": "TARGET",
            "title": "Travel organizer",
            "categories": ["Accessories"],
            "features": ["wallet leather red"],
        })
        products.extend(
            {
                "parent_asin": f"COLOR_FILLER_{index:02d}",
                "title": "Red accessory",
                "categories": ["Accessories"],
            }
            for index in range(30)
        )
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.jsonl"
            catalog.write_text(
                "".join(json.dumps(product) + "\n" for product in products),
                encoding="utf-8",
            )
            baseline = Agent(catalog, rerank=False)
            baseline.reset("baseline", {})
            baseline_response = baseline.respond(
                "baseline",
                "I'm looking for a red leather wallet.",
                1,
                10,
            )
            candidate = Agent(catalog, rerank=True)
            candidate.reset("candidate", {})
            candidate_response = candidate.respond(
                "candidate",
                "I'm looking for a red leather wallet.",
                1,
                10,
            )

        baseline_ids = [item["parent_asin"] for item in baseline_response["recommendations"]]
        candidate_ids = [item["parent_asin"] for item in candidate_response["recommendations"]]
        self.assertEqual(
            baseline_ids,
            [f"DISTRACTOR_{index:02d}" for index in range(10)],
        )
        self.assertEqual(len(candidate_ids), 10)
        self.assertIn("TARGET", candidate_ids)

    def test_follow_up_constraint_keeps_the_original_category(self) -> None:
        products = [
            {
                "parent_asin": "SHIRT",
                "title": "Cotton shirt",
                "categories": ["Clothing", "Shirts"],
                "features": ["cotton"],
            },
            {
                "parent_asin": "SHOE",
                "title": "Running shoe",
                "categories": ["Clothing", "Shoes"],
                "features": ["cotton upper"],
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.jsonl"
            catalog.write_text(
                "".join(json.dumps(product) + "\n" for product in products),
                encoding="utf-8",
            )
            agent = Agent(catalog)
            agent.reset("session", {})
            agent.respond("session", "I'm looking for running shoes.", 1, 10)
            response = agent.respond(
                "session",
                "For that, what matters is: cotton.",
                2,
                10,
            )

        self.assertEqual(response["recommendations"][0]["parent_asin"], "SHOE")

    def test_vague_request_asks_for_one_specific_constraint(self) -> None:
        products = [{
            "parent_asin": "SHOE",
            "title": "Running shoe",
            "categories": ["Clothing", "Shoes"],
        }]
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.jsonl"
            catalog.write_text(json.dumps(products[0]) + "\n", encoding="utf-8")
            agent = Agent(catalog)
            agent.reset("session", {})
            response = agent.respond(
                "session",
                "I'm looking for shoes, but I'm still exploring.",
                1,
                10,
            )

        self.assertEqual(response["ask_attribute"], "other")
        self.assertIn("requirement", response["message"].lower())

    def test_conversation_boilerplate_does_not_outrank_product_evidence(self) -> None:
        products = [
            {
                "parent_asin": "DISTRACTOR",
                "title": "Exploring what matters, additional preference",
                "categories": ["Clothing"],
            },
            {
                "parent_asin": "BOOT",
                "title": "Leather boot",
                "categories": ["Clothing", "Boots"],
                "features": ["leather"],
            },
        ]
        with tempfile.TemporaryDirectory() as directory:
            catalog = Path(directory) / "catalog.jsonl"
            catalog.write_text(
                "".join(json.dumps(product) + "\n" for product in products),
                encoding="utf-8",
            )
            agent = Agent(catalog)
            agent.reset("session", {})
            agent.respond(
                "session",
                "I'm looking for boots, but I'm still exploring.",
                1,
                10,
            )
            response = agent.respond(
                "session",
                "For that, what matters is: leather.",
                2,
                10,
            )

        self.assertEqual(response["recommendations"][0]["parent_asin"], "BOOT")


if __name__ == "__main__":
    unittest.main()
