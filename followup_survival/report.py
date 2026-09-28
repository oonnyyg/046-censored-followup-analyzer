from __future__ import annotations

import csv
import io
import json
import os
import tempfile
from pathlib import Path

from .analysis import (
    OVERALL_GROUP,
    PopulationResult,
    analyze_population,
    split_populations,
)
from .config import Config
from .constants import (
    STEP_FILENAME,
    SUMMARY_FILENAME,
    TIMEPOINT_FILENAME,
)
from .reader import Record


def build_results(
    records: list[Record], config: Config
) -> list[PopulationResult]:
    return [
        analyze_population(name, population, config.query_days)
        for name, population in split_populations(records)
    ]


def render_step_csv(results: list[PopulationResult]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["scope", "group", "day", "at_risk", "events",
         "censored", "survival_after"]
    )
    for result in results:
        scope = "overall" if result.name == OVERALL_GROUP else "group"
        for step in result.steps:
            writer.writerow(
                [
                    scope,
                    result.name,
                    step.day,
                    step.at_risk,
                    step.events,
                    step.censored,
                    f"{step.survival_after:.6f}",
                ]
            )
    return buffer.getvalue()


def render_timepoint_csv(results: list[PopulationResult]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["scope", "group", "query_day", "at_risk",
         "survival", "out_of_followup"]
    )
    for result in results:
        scope = "overall" if result.name == OVERALL_GROUP else "group"
        for row in result.timepoints:
            survival = (
                "" if row.survival is None else f"{row.survival:.6f}"
            )
            writer.writerow(
                [
                    scope,
                    result.name,
                    row.query_day,
                    row.at_risk,
                    survival,
                    "true" if row.out_of_followup else "false",
                ]
            )
    return buffer.getvalue()


def render_summary_json(
    results: list[PopulationResult], config: Config
) -> str:
    groups_payload = []
    for result in results:
        if result.name == OVERALL_GROUP:
            continue
        groups_payload.append(_summary_entry(result))

    overall = next(item for item in results if item.name == OVERALL_GROUP)
    payload = {
        "query_days": list(config.query_days),
        "overall": _summary_entry(overall),
        "groups": groups_payload,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def _summary_entry(result: PopulationResult) -> dict:
    if result.median_survival_days is None:
        median_note = (
            "survival probability never reached 0.5 or below within "
            "observed follow-up"
        )
    else:
        median_note = "first event day at which survival <= 0.5"
    return {
        "group": result.name,
        "subject_count": result.subject_count,
        "event_count": result.event_count,
        "censored_count": result.censored_count,
        "median_survival_days": result.median_survival_days,
        "median_survival_note": median_note,
    }


def write_reports(
    records: list[Record], config: Config, output_dir: str | Path
) -> None:
    results = build_results(records, config)
    contents = {
        STEP_FILENAME: render_step_csv(results),
        TIMEPOINT_FILENAME: render_timepoint_csv(results),
        SUMMARY_FILENAME: render_summary_json(results, config),
    }

    target_dir = Path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)

    temp_paths: list[Path] = []
    try:
        for filename, content in contents.items():
            fd, temp_name = tempfile.mkstemp(
                prefix=f".{filename}.", suffix=".tmp", dir=target_dir
            )
            with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
                handle.write(content)
            temp_paths.append(Path(temp_name))
        for temp_path, filename in zip(temp_paths, contents):
            os.replace(temp_path, target_dir / filename)
    finally:
        for temp_path in temp_paths:
            if temp_path.exists():
                temp_path.unlink()
