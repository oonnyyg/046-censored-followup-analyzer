from __future__ import annotations

import csv
import re
from dataclasses import dataclass
from pathlib import Path

from .config import Config
from .constants import OVERALL_GROUP
from .errors import InputError

_DIGITS = re.compile(r"[0-9]+$")


@dataclass(frozen=True)
class Record:
    id: str
    group: str
    days: int
    event: int


def read_records(path: str | Path, config: Config) -> list[Record]:
    with open(path, "r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise InputError("records file: empty data table (no header row)")

        required = [
            config.id_column,
            config.group_column,
            config.days_column,
            config.event_column,
        ]
        missing_columns = [name for name in required if name not in reader.fieldnames]
        if missing_columns:
            raise InputError(
                f"records file: missing required column "
                f"'{missing_columns[0]}'"
            )

        records: list[Record] = []
        seen_ids: set[str] = set()
        for line_number, raw_row in enumerate(reader, start=2):
            record = _parse_row(raw_row, config, line_number)
            if record.id in seen_ids:
                raise InputError(
                    f"records row {line_number}: duplicate id '{record.id}'"
                )
            seen_ids.add(record.id)
            records.append(record)

    if not records:
        raise InputError("records file: empty data table (no data rows)")
    return records


def _parse_row(raw_row: dict, config: Config, line_number: int) -> Record:
    def cell(name: str) -> str:
        value = raw_row.get(name)
        if value is None:
            raise InputError(
                f"records row {line_number}: missing value for column '{name}'"
            )
        text = value.strip()
        if text == "":
            raise InputError(
                f"records row {line_number}: empty value in column '{name}'"
            )
        return text

    subject_id = cell(config.id_column)
    group = cell(config.group_column)
    if group == OVERALL_GROUP:
        raise InputError(
            f"records row {line_number}: group name '{OVERALL_GROUP}' is reserved"
        )

    days_text = cell(config.days_column)
    if _DIGITS.fullmatch(days_text) is None:
        raise InputError(
            f"records row {line_number}: follow-up days must be a non-negative "
            f"integer, got '{days_text}'"
        )
    days = int(days_text)

    event_text = cell(config.event_column)
    if event_text not in ("0", "1"):
        raise InputError(
            f"records row {line_number}: event flag must be 0 (censored) or "
            f"1 (event), got '{event_text}'"
        )

    return Record(
        id=subject_id, group=group, days=days, event=int(event_text)
    )
