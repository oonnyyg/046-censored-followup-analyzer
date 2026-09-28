import unittest

from followup_survival.analysis import (
    OVERALL_GROUP,
    analyze_population,
    split_populations,
)
from followup_survival.reader import Record


def rec(subject_id, group, days, event):
    return Record(id=subject_id, group=group, days=days, event=event)


class AnalysisTests(unittest.TestCase):
    def test_same_day_event_and_censoring_order_independent(self):
        records_a = [
            rec("1", "g", 3, 1),
            rec("2", "g", 3, 0),
            rec("3", "g", 5, 0),
        ]
        records_b = list(reversed(records_a))
        result_a = analyze_population("g", records_a, (3, 5))
        result_b = analyze_population("g", records_b, (3, 5))

        day3 = result_a.steps[0]
        self.assertEqual((day3.at_risk, day3.events, day3.censored), (3, 1, 1))
        self.assertAlmostEqual(day3.survival_after, 2 / 3)
        self.assertEqual(
            [(s.day, s.survival_after) for s in result_a.steps],
            [(s.day, s.survival_after) for s in result_b.steps],
        )
        self.assertAlmostEqual(result_a.timepoints[0].survival, 2 / 3)

    def test_all_censored_never_drops_and_median_null(self):
        records = [rec("1", "g", 1, 0), rec("2", "g", 4, 0)]
        result = analyze_population("g", records, (0, 4, 5))
        self.assertTrue(all(step.events == 0 for step in result.steps))
        self.assertTrue(
            all(step.survival_after == 1.0 for step in result.steps)
        )
        self.assertIsNone(result.median_survival_days)
        self.assertFalse(result.timepoints[1].out_of_followup)
        self.assertIsNone(result.timepoints[2].survival)
        self.assertTrue(result.timepoints[2].out_of_followup)
        self.assertEqual(result.timepoints[2].at_risk, 0)

    def test_day_zero_event(self):
        records = [rec("1", "g", 0, 1), rec("2", "g", 0, 0)]
        result = analyze_population("g", records, (0,))
        step = result.steps[0]
        self.assertEqual((step.day, step.at_risk, step.events, step.censored),
                         (0, 2, 1, 1))
        self.assertAlmostEqual(step.survival_after, 0.5)
        self.assertAlmostEqual(result.timepoints[0].survival, 0.5)

    def test_survival_stays_zero_after_reaching_zero(self):
        records = [
            rec("1", "g", 2, 1),
            rec("2", "g", 5, 1),
            rec("3", "g", 5, 1),
        ]
        result = analyze_population("g", records, (5, 6))
        self.assertAlmostEqual(result.steps[0].survival_after, 2 / 3)
        self.assertAlmostEqual(result.steps[1].survival_after, 0.0)
        self.assertAlmostEqual(result.timepoints[0].survival, 0.0)
        self.assertTrue(result.timepoints[0].query_day == 5)
        self.assertIsNone(result.timepoints[1].survival)
        self.assertTrue(result.timepoints[1].out_of_followup)

    def test_multiple_groups_sorted_with_overall_first(self):
        records = [
            rec("1", "beta", 1, 1),
            rec("2", "alpha", 1, 0),
            rec("3", "beta", 2, 0),
        ]
        populations = split_populations(records)
        self.assertEqual(
            [name for name, _ in populations],
            [OVERALL_GROUP, "alpha", "beta"],
        )
        overall = populations[0][1]
        self.assertEqual(len(overall), 3)

    def test_timepoint_boundaries(self):
        records = [
            rec("1", "g", 3, 1),
            rec("2", "g", 6, 1),
            rec("3", "g", 6, 1),
        ]
        result = analyze_population("g", records, (0, 2, 3, 4, 6, 7))
        values = [
            (row.query_day, row.at_risk, row.survival, row.out_of_followup)
            for row in result.timepoints
        ]
        self.assertEqual(values[0][:2], (0, 3))
        self.assertAlmostEqual(values[0][2], 1.0)
        self.assertAlmostEqual(values[1][2], 1.0)
        self.assertAlmostEqual(values[2][2], 2 / 3)
        self.assertEqual(values[2][1], 3)
        self.assertAlmostEqual(values[3][2], 2 / 3)
        self.assertEqual(values[4], (6, 2, 0.0, False))
        self.assertEqual(values[5], (7, 0, None, True))
        self.assertEqual(result.median_survival_days, 6)


if __name__ == "__main__":
    unittest.main()
