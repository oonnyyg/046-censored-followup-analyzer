import json
import os
import tempfile
import unittest

from followup_survival.__main__ import main
from followup_survival.errors import FollowupError
from followup_survival.validation import load_query_days, load_records


class ValidationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name

    def tearDown(self):
        self.tmp.cleanup()

    def _write_csv(self, text):
        path = os.path.join(self.dir, "records.csv")
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_empty_table_rejected(self):
        path = self._write_csv("id,group,days,event\n")
        with self.assertRaisesRegex(FollowupError, "data table is empty"):
            load_records(path)

    def test_duplicate_id_located(self):
        path = self._write_csv(
            "id,group,days,event\n"
            "a,g,1,1\n"
            "b,g,2,0\n"
            "a,g,3,0\n"
        )
        with self.assertRaisesRegex(FollowupError, r"row 4.*duplicate id"):
            load_records(path)

    def test_missing_field_and_bad_event(self):
        path = self._write_csv("id,group,days,event\n,g,1,1\n")
        with self.assertRaisesRegex(FollowupError, r"row 2.*id is empty"):
            load_records(path)

        path = self._write_csv("id,group,days,event\na,g,1,X\n")
        with self.assertRaisesRegex(FollowupError, r"row 2.*event must be 0 or 1"):
            load_records(path)

    def test_negative_and_fractional_days(self):
        path = self._write_csv("id,group,days,event\na,g,-1,1\n")
        with self.assertRaises(FollowupError):
            load_records(path)
        path = self._write_csv("id,group,days,event\na,g,1.5,1\n")
        with self.assertRaises(FollowupError):
            load_records(path)

    def _write_config(self, payload):
        path = os.path.join(self.dir, "config.json")
        with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle)
        return path

    def test_config_dedup_sorted(self):
        path = self._write_config({"query_days": [5, 0, 5, 2]})
        self.assertEqual(load_query_days(path), [0, 2, 5])

    def test_config_empty_and_negative(self):
        path = self._write_config({"query_days": []})
        with self.assertRaisesRegex(FollowupError, "non-empty"):
            load_query_days(path)
        path = self._write_config({"query_days": [-1]})
        with self.assertRaisesRegex(FollowupError, r"query_days\[0\]"):
            load_query_days(path)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = self.tmp.name
        self.csv_path = os.path.join(self.dir, "records.csv")
        self.cfg_path = os.path.join(self.dir, "config.json")
        self.out_dir = os.path.join(self.dir, "out")
        with open(self.csv_path, "w", encoding="utf-8") as handle:
            handle.write(
                "id,group,days,event\n"
                "a,A,0,1\nb,A,4,1\nc,A,4,0\nd,B,6,0\n"
            )
        with open(self.cfg_path, "w", encoding="utf-8") as handle:
            json.dump({"query_days": [0, 4, 7]}, handle)

    def tearDown(self):
        self.tmp.cleanup()

    def test_end_to_end(self):
        code = main(["--records", self.csv_path,
                     "--config", self.cfg_path, "--out", self.out_dir])
        self.assertEqual(code, 0)
        for name in ("ladder.csv", "timepoints.csv", "summary.json"):
            self.assertTrue(os.path.exists(os.path.join(self.out_dir, name)))
        with open(os.path.join(self.out_dir, "timepoints.csv"), encoding="utf-8") as f:
            text = f.read()
        self.assertIn("true", text.splitlines()[-1].split(",")[-1:][0])

    def test_invalid_input_does_not_overwrite_old_results(self):
        self.assertEqual(main(["--records", self.csv_path,
                              "--config", self.cfg_path, "--out", self.out_dir]), 0)
        before = {}
        for name in ("ladder.csv", "timepoints.csv", "summary.json"):
            path = os.path.join(self.out_dir, name)
            with open(path, encoding="utf-8") as handle:
                before[name] = handle.read()

        bad_csv = os.path.join(self.dir, "bad.csv")
        with open(bad_csv, "w", encoding="utf-8") as handle:
            handle.write("id,group,days,event\na,A,0,1\na,A,4,0\n")
        code = main(["--records", bad_csv,
                     "--config", self.cfg_path, "--out", self.out_dir])
        self.assertNotEqual(code, 0)
        for name, old in before.items():
            with open(os.path.join(self.out_dir, name), encoding="utf-8") as handle:
                self.assertEqual(handle.read(), old)


if __name__ == "__main__":
    unittest.main()
