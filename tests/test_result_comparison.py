from __future__ import annotations

import unittest

from evaluator.result_comparison import compare_results


class ResultComparisonTest(unittest.TestCase):
    def test_reports_fixed_broken_and_rank_changes(self) -> None:
        baseline = {
            "hit_rate_at_10": 0.5,
            "mrr": 0.375,
            "mttc": 7.0,
            "efficiency": 0.4,
            "recommended_technical_score": 0.4,
            "sessions": [
                {
                    "sample_id": "buying_fixed",
                    "scenario_type": "buying",
                    "hit": False,
                    "first_hit_turn": None,
                    "best_rank": None,
                },
                {
                    "sample_id": "browsing_broken",
                    "scenario_type": "browsing",
                    "hit": True,
                    "first_hit_turn": 2,
                    "best_rank": 2,
                },
                {
                    "sample_id": "rank_better",
                    "scenario_type": "buying",
                    "hit": True,
                    "first_hit_turn": 3,
                    "best_rank": 4,
                },
                {
                    "sample_id": "rank_worse",
                    "scenario_type": "browsing",
                    "hit": True,
                    "first_hit_turn": 1,
                    "best_rank": 1,
                },
            ],
        }
        candidate = {
            "hit_rate_at_10": 0.75,
            "mrr": 0.5,
            "mttc": 5.5,
            "efficiency": 0.6,
            "recommended_technical_score": 0.6,
            "sessions": [
                {
                    "sample_id": "buying_fixed",
                    "scenario_type": "buying",
                    "hit": True,
                    "first_hit_turn": 2,
                    "best_rank": 1,
                },
                {
                    "sample_id": "browsing_broken",
                    "scenario_type": "browsing",
                    "hit": False,
                    "first_hit_turn": None,
                    "best_rank": None,
                },
                {
                    "sample_id": "rank_better",
                    "scenario_type": "buying",
                    "hit": True,
                    "first_hit_turn": 2,
                    "best_rank": 2,
                },
                {
                    "sample_id": "rank_worse",
                    "scenario_type": "browsing",
                    "hit": True,
                    "first_hit_turn": 2,
                    "best_rank": 3,
                },
            ],
        }

        comparison = compare_results(baseline, candidate)

        self.assertEqual(comparison["fixed_session_ids"], ["buying_fixed"])
        self.assertEqual(comparison["broken_session_ids"], ["browsing_broken"])
        self.assertEqual(comparison["rank_improved_session_ids"], ["rank_better"])
        self.assertEqual(comparison["rank_regressed_session_ids"], ["rank_worse"])
        self.assertEqual(comparison["turn_improved_session_ids"], ["rank_better"])
        self.assertEqual(comparison["turn_regressed_session_ids"], ["rank_worse"])
        self.assertEqual(comparison["metric_deltas"]["hit_rate_at_10"], 0.25)
        self.assertEqual(
            comparison["scenario_changes"]["buying"]["fixed_session_ids"],
            ["buying_fixed"],
        )
        self.assertEqual(
            comparison["scenario_changes"]["browsing"]["broken_session_ids"],
            ["browsing_broken"],
        )

    def test_rejects_results_with_different_session_ids(self) -> None:
        metrics = {
            "hit_rate_at_10": 1.0,
            "mrr": 1.0,
            "mttc": 1.0,
            "efficiency": 1.0,
            "recommended_technical_score": 1.0,
        }
        baseline = {
            **metrics,
            "sessions": [{
                "sample_id": "A",
                "scenario_type": "buying",
                "hit": True,
                "first_hit_turn": 1,
                "best_rank": 1,
            }]
        }
        candidate = {
            **metrics,
            "sessions": [{
                "sample_id": "B",
                "scenario_type": "buying",
                "hit": True,
                "first_hit_turn": 1,
                "best_rank": 1,
            }]
        }

        with self.assertRaisesRegex(ValueError, "same session IDs"):
            compare_results(baseline, candidate)

    def test_rejects_a_missing_aggregate_metric(self) -> None:
        baseline = {
            "hit_rate_at_10": 1.0,
            "mttc": 1.0,
            "efficiency": 1.0,
            "recommended_technical_score": 1.0,
            "sessions": [
                {
                    "sample_id": "A",
                    "scenario_type": "buying",
                    "hit": True,
                    "first_hit_turn": 1,
                    "best_rank": 1,
                }
            ],
        }
        candidate = {**baseline, "mrr": 1.0}

        with self.assertRaisesRegex(ValueError, "metric mrr"):
            compare_results(baseline, candidate)

    def test_rejects_a_hit_without_a_valid_rank(self) -> None:
        metrics = {
            "hit_rate_at_10": 1.0,
            "mrr": 1.0,
            "mttc": 1.0,
            "efficiency": 1.0,
            "recommended_technical_score": 1.0,
        }
        baseline = {
            **metrics,
            "sessions": [
                {
                    "sample_id": "A",
                    "scenario_type": "buying",
                    "hit": True,
                    "first_hit_turn": 1,
                    "best_rank": None,
                }
            ],
        }
        candidate = {
            **metrics,
            "sessions": [
                {
                    "sample_id": "A",
                    "scenario_type": "buying",
                    "hit": True,
                    "first_hit_turn": 1,
                    "best_rank": 1,
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "best_rank"):
            compare_results(baseline, candidate)

    def test_rejects_a_hit_without_a_valid_turn(self) -> None:
        metrics = {
            "hit_rate_at_10": 1.0,
            "mrr": 1.0,
            "mttc": 1.0,
            "efficiency": 1.0,
            "recommended_technical_score": 1.0,
        }
        invalid = {
            **metrics,
            "sessions": [
                {
                    "sample_id": "A",
                    "scenario_type": "buying",
                    "hit": True,
                    "first_hit_turn": None,
                    "best_rank": 1,
                }
            ],
        }
        valid = {
            **metrics,
            "sessions": [
                {
                    "sample_id": "A",
                    "scenario_type": "buying",
                    "hit": True,
                    "first_hit_turn": 1,
                    "best_rank": 1,
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "first_hit_turn"):
            compare_results(invalid, valid)

    def test_rejects_a_boolean_aggregate_metric(self) -> None:
        result = {
            "hit_rate_at_10": True,
            "mrr": 1.0,
            "mttc": 1.0,
            "efficiency": 1.0,
            "recommended_technical_score": 1.0,
            "sessions": [
                {
                    "sample_id": "A",
                    "scenario_type": "buying",
                    "hit": True,
                    "first_hit_turn": 1,
                    "best_rank": 1,
                }
            ],
        }

        with self.assertRaisesRegex(ValueError, "metric hit_rate_at_10"):
            compare_results(result, result)


if __name__ == "__main__":
    unittest.main()
