from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .errors import ConfigError

DEFAULT_COLUMNS = {
    "id_column": "id",
    "group_column": "group",
    "days_column": "days",
    "event_column": "event",
}

_KNOWN_KEYS = frozenset(DEFAULT_COLUMNS) | {"query_days"}


@dataclass(frozen=True)
class Config:
    query_days: tuple[int, ...]
    id_column: str
    group_column: str
    days_column: str
    event_column: str


def load_config(path: str | Path) -> Config:
    with open(path, "r", encoding="utf-8-sig") as handle:
        try:
            raw = json.load(handle)
        except json.JSONDecodeError as exc:
            raise ConfigError(
                f"config item <root>: invalid JSON: {exc.msg} "
                f"(line {exc.lineno}, column {exc.colno})"
            ) from exc
    return parse_config(raw)


def parse_config(raw: object) -> Config:
    if not isinstance(raw, dict):
        raise ConfigError("config item <root>: configuration must be a JSON object")

    unknown = sorted(set(raw) - _KNOWN_KEYS)
    if unknown:
        raise ConfigError(
            f"config item '{unknown[0]}': unknown configuration key"
        )

    if "query_days" not in raw:
        raise ConfigError("config item 'query_days': required key is missing")
    query_raw = raw["query_days"]
    if not isinstance(query_raw, list) or len(query_raw) == 0:
        raise ConfigError(
            "config item 'query_days': must be a non-empty list"
        )

    query_days: list[int] = []
    for index, value in enumerate(query_raw):
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ConfigError(
                f"config item 'query_days[{index}]': must be a non-negative integer"
            )
        query_days.append(value)
    query_days = sorted(set(query_days))

    columns: dict[str, str] = {}
    for key, default in DEFAULT_COLUMNS.items():
        value = raw.get(key, default)
        if not isinstance(value, str) or value == "":
            raise ConfigError(
                f"config item '{key}': column name must be a non-empty string"
            )
        columns[key] = value

    names = list(columns.values())
    if len(set(names)) != len(names):
        raise ConfigError(
            "config item <root>: configured column names must be distinct"
        )

    return Config(query_days=tuple(query_days), **columns)
