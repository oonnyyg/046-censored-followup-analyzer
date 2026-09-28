import json
import tempfile
import unittest
from pathlib import Path

from followup_survival.config import parse_config
from followup_survival.errors import ConfigError, InputError
from followup_survival.reader import read_records


def config(**overrides):
    raw = {"query_days": [1]}
    raw.update(overrides)
    return parse_config(raw)


class ConfigTests(unittest.TestCase):
    def test_query_days_must_be_nonempty_list(self):
        with self.assertRaises(ConfigError):
            parse_config({"query_days": []})
        with self.assertRaises(ConfigError):
            parse_config({})

    def test_query_day_must_be_non_negative_int(self):
        with self.assertRaises(ConfigError):
            parse_config({"query_days": [-1]})
        with self.assertRaises(ConfigError):
            parse_config({"query_days": [True]})
        with self.assertRaises(ConfigError):
            parse_config({"query_days": ["2"]})

    def test_query_days_deduplicated_and_sorted(self):
        cfg = parse_config({"query_days": [5, 0, 5, 2]})
        self.assertEqual(cfg.query_days, (0, 2, 5))

    def test_unknown_key_rejected(self):
        with self.assertRaises(ConfigError):
            parse_config({"query_days": [1], "bogus": 2})


class ReaderTests(unittest.TestCase):
    def _write(self, content: str) -> Path:
        directory = Path(tempfile.mkdtemp())
        path = directory / "records.csv"
        path.write_text(content, encoding="utf-8")
        return path

    def test_empty_table_rejected(self):
        path = self._write("")
        with self.assertRaises(InputError):
            read_records(path, config())

    def test_header_only_rejected(self):
        path = self._write("id,group,days,event\n")
        with self.assertRaises(InputError):
            read_records(path, config())

    def test_duplicate_id_rejected(self):
        path = self._write(
            "id,group,days,event\n"
            "a,g,1,1\na,g,2,0\n"
        )
        with self.assertRaisesRegex(InputError, "row 3"):
            read_records(path, config())

    def test_missing_and_empty_fields_rejected(self):
        bad_days = self._write("id,group,days,event\na,g,,1\n")
        with self.assertRaisesRegex(InputError, "row 2"):
            read_records(bad_days, config())
        bad_flag = self._write("id,group,days,event\na,g,3,2\n")
        with self.assertRaisesRegex(InputError, "row 2"):
            read_records(bad_flag, config())
        bad_days_value = self._write("id,group,days,event\na,g,-1,1\n")
        with self.assertRaisesRegex(InputError, "row 2"):
            read_records(bad_days_value, config())

    def test_reserved_group_name_rejected(self):
        path = self._write("id,group,days,event\na,__overall__,1,1\n")
        with self.assertRaises(InputError):
            read_records(path, config())

    def test_missing_column_rejected(self):
        path = self._write("id,group,days\na,g,1\n")
        with self.assertRaises(InputError):
            read_records(path, config())

    def test_custom_columns_accepted(self):
        path = self._write(
            "patient,arm,followup,status,extra\n"
            "a,g,1,1,ignore\n"
        )
        cfg = config(
            id_column="patient",
            group_column="arm",
            days_column="followup",
            event_column="status",
        )
        records = read_records(path, cfg)
        self.assertEqual(records[0].id, "a")


if __name__ == "__main__":
    unittest.main()
