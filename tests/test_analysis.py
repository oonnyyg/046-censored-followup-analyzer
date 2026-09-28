import unittest

from followup_survival.analysis import aggregate, analyze_all, query_at
from followup_survival.validation import Record


def rec(rid, group, days, event):
    return Record(rid, group, days, event)


class AggregationTests(unittest.TestCase):
    def test_same_day_event_and_censoring_order_independent(self):
        rows_a = [rec("1", "g", 5, 1), rec("2", "g", 5, 0), rec("3", "g", 5, 1)]
        rows_b = list(reversed(rows_a))
        result_a = aggregate(rows_a, "g")
        result_b = aggregate(rows_b, "g")
        details = [(s.days, s.at_risk, s.events, s.censored) for s in result_a.steps]
        self.assertEqual(details, [(5, 3, 2, 1)])
        self.assertAlmostEqual(result_a.steps[0].survival, 1 / 3)
        self.assertEqual(result_a.steps, result_b.steps)

    def test_censoring_does_not_lower_survival(self):
        result = aggregate([rec("a", "g", 2, 0), rec("b", "g", 4, 0)], "g")
        self.assertEqual([s.survival for s in result.steps], [1.0, 1.0])
        self.assertIsNone(result.median_days)

    def test_zero_day_event(self):
        result = aggregate([rec("a", "g", 0, 1), rec("b", "g", 3, 0)], "g")
        self.assertEqual(result.steps[0].at_risk, 2)
        self.assertEqual(result.steps[0].survival, 0.5)
        self.assertEqual(result.median_days, 0)

    def test_zero_stays_zero(self):
        result = aggregate(
            [rec("a", "g", 1, 1), rec("b", "g", 1, 1), rec("c", "g", 5, 0)], "g"
        )
        self.assertAlmostEqual(result.steps[0].survival, 1 / 3)

        all_events = aggregate(
            [rec("a", "g", 0, 0),
             rec("b", "g", 2, 1), rec("c", "g", 2, 1),
             rec("d", "g", 2, 1)],
            "g",
        )
        # day 0 censoring keeps 1; day 2 all remaining have events -> 0
        self.assertEqual([s.survival for s in all_events.steps], [1.0, 0.0])

    def test_multiple_groups_and_overall(self):
        records = [rec("a", "B", 1, 1), rec("b", "A", 2, 0), rec("c", "A", 3, 1)]
        results = analyze_all(records)
        self.assertEqual([r.name for r in results], ["overall", "A", "B"])
        overall = results[0]
        self.assertEqual((overall.n, overall.events, overall.censored), (3, 2, 1))


class QueryTests(unittest.TestCase):
    def setUp(self):
        self.result = aggregate(
            [rec("a", "g", 0, 1), rec("b", "g", 5, 1), rec("c", "g", 5, 0),
             rec("d", "g", 9, 0)],
            "g",
        )

    def test_before_first_observation_is_one(self):
        point = query_at(self.result, 0)
        self.assertEqual(point.survival, 0.75)
        self.assertEqual(point.at_risk, 4)

    def test_between_days_uses_latest(self):
        point = query_at(self.result, 4)
        self.assertAlmostEqual(point.survival, 0.75)
        self.assertEqual(point.at_risk, 3)

    def test_event_day_uses_post_drop(self):
        point = query_at(self.result, 5)
        self.assertAlmostEqual(point.survival, 0.5)
        self.assertEqual(point.at_risk, 3)

    def test_beyond_max_is_null(self):
        point = query_at(self.result, 10)
        self.assertIsNone(point.survival)
        self.assertTrue(point.out_of_followup)
        self.assertEqual(point.at_risk, 0)


if __name__ == "__main__":
    unittest.main()
