"""CSV record loading and JSON config validation."""

import csv
import json
from dataclasses import dataclass

from .errors import FollowupError

ID_COLUMN = "id"
GROUP_COLUMN = "group"
DAYS_COLUMN = "days"
EVENT_COLUMN = "event"
REQUIRED_COLUMNS = (ID_COLUMN, GROUP_COLUMN, DAYS_COLUMN, EVENT_COLUMN)


@dataclass(frozen=True)
class Record:
    id: str
    group: str
    days: int
    event: int


def load_records(csv_path: str) -> list[Record]:
    """Load and fully validate the follow-up CSV.

    Row numbers in errors refer to the CSV data line (header = line 1).
    """
    try:
        handle = open(csv_path, "r", encoding="utf-8-sig", newline="")
    except OSError as exc:
        raise FollowupError(f"cannot read CSV: {exc}") from exc
    with handle:
        reader = csv.reader(handle)
        try:
            header = next(reader)
        except StopIteration:
            raise FollowupError("CSV is empty")
        normalized = [c.strip() for c in header]
        missing = [c for c in REQUIRED_COLUMNS if c not in normalized]
        if missing:
            raise FollowupError(
                f"missing required column(s): {', '.join(missing)}", "header"
            )
        index = {c: normalized.index(c) for c in REQUIRED_COLUMNS}

        records: list[Record] = []
        seen_ids: set[str] = set()
        row_no = 1
        for raw in reader:
            row_no += 1
            if not raw or all(c.strip() == "" for c in raw):
                raise FollowupError("empty row", f"row {row_no}")
            loc = f"row {row_no}"
            if len(raw) < len(header):
                raise FollowupError("row has fewer fields than header", loc)

            rec_id = raw[index[ID_COLUMN]].strip()
            group = raw[index[GROUP_COLUMN]].strip()
            days_text = raw[index[DAYS_COLUMN]].strip()
            event_text = raw[index[EVENT_COLUMN]].strip()

            if not rec_id:
                raise FollowupError("id is empty", loc)
            if rec_id in seen_ids:
                raise FollowupError(f"duplicate id {rec_id!r}", loc)
            if not group:
                raise FollowupError("group is empty", loc)
            days = _parse_nonneg_int(days_text, "days", loc)
            if event_text not in ("0", "1"):
                raise FollowupError(
                    f"event must be 0 or 1, got {event_text!r}", loc
                )

            seen_ids.add(rec_id)
            records.append(
                Record(id=rec_id, group=group, days=days, event=int(event_text))
            )

    if not records:
        raise FollowupError("data table is empty")
    return records


def _parse_nonneg_int(text: str, name: str, loc: str) -> int:
    if text == "":
        raise FollowupError(f"{name} is empty", loc)
    try:
        value = int(text)
    except ValueError:
        raise FollowupError(
            f"{name} must be a non-negative integer, got {text!r}", loc
        ) from None
    if value < 0 or str(value) != text:
        raise FollowupError(
            f"{name} must be a non-negative integer, got {text!r}", loc
        )
    return value


def load_query_days(json_path: str) -> list[int]:
    """Load, validate, de-duplicate and sort the query-days config."""
    try:
        with open(json_path, "r", encoding="utf-8-sig") as handle:
            config = json.load(handle)
    except OSError as exc:
        raise FollowupError(f"cannot read config: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise FollowupError(f"invalid JSON: {exc}", "config") from exc

    if not isinstance(config, dict) or "query_days" not in config:
        raise FollowupError("config must be an object with 'query_days'", "config")
    raw_days = config["query_days"]
    loc = "config.query_days"
    if not isinstance(raw_days, list) or not raw_days:
        raise FollowupError("query_days must be a non-empty list", loc)
    days: list[int] = []
    for pos, item in enumerate(raw_days):
        item_loc = f"{loc}[{pos}]"
        if isinstance(item, bool) or not isinstance(item, int):
            raise FollowupError(
                f"query day must be a non-negative integer, got {item!r}",
                item_loc,
            )
        if item < 0:
            raise FollowupError(
                f"query day must be non-negative, got {item}", item_loc
            )
        days.append(item)
    return sorted(set(days))
