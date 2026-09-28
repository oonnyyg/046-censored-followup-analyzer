import io
import json
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path

from followup_survival.cli import main
from followup_survival.constants import (
    STEP_FILENAME,
    SUMMARY_FILENAME,
    TIMEPOINT_FILENAME,
)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.directory = Path(tempfile.mkdtemp())
        self.records = self.directory / "records.csv"
        self.config = self.directory / "config.json"
        self.output = self.directory / "out"

    def _write_inputs(self, csv_text, query_days=(0, 2, 5)):
        self.records.write_text(csv_text, encoding="utf-8")
        self.config.write_text(
            json.dumps({"query_days": list(query_days)}), encoding="utf-8"
        )

    def _run(self):
        return main(
            [
                "--records", str(self.records),
                "--config", str(self.config),
                "--output-dir", str(self.output),
            ]
        )

    def test_success_writes_three_reports(self):
        self._write_inputs(
            "id,group,days,event\n"
            "p1,A,0,1\np2,A,2,1\np3,A,2,0\np4,B,5,0\n"
        )
        self.assertEqual(self._run(), 0)
        for filename in (STEP_FILENAME, TIMEPOINT_FILENAME, SUMMARY_FILENAME):
            self.assertTrue((self.output / filename).exists())

        summary = json.loads((self.output / SUMMARY_FILENAME).read_text("utf-8"))
        self.assertEqual(summary["overall"]["subject_count"], 4)
        self.assertEqual(summary["overall"]["event_count"], 2)
        self.assertEqual(summary["overall"]["censored_count"], 2)
        self.assertEqual([g["group"] for g in summary["groups"]], ["A", "B"])

    def test_invalid_input_does_not_overwrite_old_results(self):
        self._write_inputs(
            "id,group,days,event\np1,A,1,1\n"
        )
        self.assertEqual(self._run(), 0)
        old_step = (self.output / STEP_FILENAME).read_text("utf-8")

        self.records.write_text(
            "id,group,days,event\np1,A,1,1\np1,A,2,0\n",
            encoding="utf-8",
        )
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = self._run()
        self.assertEqual(code, 1)
        self.assertIn("duplicate id", buffer.getvalue())
        self.assertEqual(
            (self.output / STEP_FILENAME).read_text("utf-8"), old_step
        )

    def test_invalid_config_exits_nonzero(self):
        self._write_inputs("id,group,days,event\np1,A,1,1\n")
        self.config.write_text(
            json.dumps({"query_days": []}), encoding="utf-8"
        )
        buffer = io.StringIO()
        with redirect_stderr(buffer):
            code = self._run()
        self.assertEqual(code, 1)
        self.assertIn("query_days", buffer.getvalue())


if __name__ == "__main__":
    unittest.main()
