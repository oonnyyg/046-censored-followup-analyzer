"""Render ladder CSV, time-point report CSV and summary JSON."""

import csv
import io
import json

from .analysis import OVERALL, GroupResult, query_at

LADDER_FILENAME = "ladder.csv"
TIMEPOINT_FILENAME = "timepoints.csv"
SUMMARY_FILENAME = "summary.json"


def render_ladder(results: list[GroupResult]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["scope", "group", "days", "at_risk", "events", "censored", "survival"]
    )
    for result in results:
        scope = "overall" if result.name == OVERALL else "group"
        for step in result.steps:
            writer.writerow(
                [
                    scope,
                    result.name,
                    step.days,
                    step.at_risk,
                    step.events,
                    step.censored,
                    f"{step.survival:.12g}",
                ]
            )
    return buffer.getvalue()


def render_timepoints(results: list[GroupResult], query_days: list[int]) -> str:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        [
            "scope",
            "group",
            "query_day",
            "at_risk",
            "survival",
            "out_of_followup",
        ]
    )
    for result in results:
        scope = "overall" if result.name == OVERALL else "group"
        for day in query_days:
            point = query_at(result, day)
            writer.writerow(
                [
                    scope,
                    result.name,
                    point.days,
                    point.at_risk,
                    "" if point.survival is None else f"{point.survival:.12g}",
                    "true" if point.out_of_followup else "false",
                ]
            )
    return buffer.getvalue()


def render_summary(results: list[GroupResult], query_days: list[int]) -> str:
    groups = [r for r in results if r.name != OVERALL]
    overall = next(r for r in results if r.name == OVERALL)

    def entry(result: GroupResult) -> dict:
        median_note = None
        if result.median_days is None:
            median_note = "survival never reached 0.5 within follow-up"
        return {
            "group": result.name,
            "subjects": result.n,
            "events": result.events,
            "censored": result.censored,
            "median_survival_days": result.median_days,
            "median_note": median_note,
        }

    payload = {
        "overall": {
            **entry(overall),
            "max_followup_days": overall.steps[-1].days if overall.steps else 0,
        },
        "groups": [entry(g) for g in groups],
        "query_days": query_days,
    }
    return json.dumps(payload, indent=2, ensure_ascii=False) + "\n"


def build_outputs(
    results: list[GroupResult], query_days: list[int]
) -> dict[str, str]:
    return {
        LADDER_FILENAME: render_ladder(results),
        TIMEPOINT_FILENAME: render_timepoints(results, query_days),
        SUMMARY_FILENAME: render_summary(results, query_days),
    }
