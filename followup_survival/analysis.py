from __future__ import annotations

from dataclasses import dataclass

from .constants import OVERALL_GROUP
from .reader import Record


@dataclass(frozen=True)
class StepRow:
    day: int
    at_risk: int
    events: int
    censored: int
    survival_after: float


@dataclass(frozen=True)
class TimepointRow:
    query_day: int
    at_risk: int
    survival: float | None
    out_of_followup: bool


@dataclass(frozen=True)
class PopulationResult:
    name: str
    subject_count: int
    event_count: int
    censored_count: int
    max_day: int
    steps: tuple[StepRow, ...]
    timepoints: tuple[TimepointRow, ...]
    median_survival_days: int | None


def split_populations(
    records: list[Record],
) -> list[tuple[str, list[Record]]]:
    groups: dict[str, list[Record]] = {}
    for record in records:
        groups.setdefault(record.group, []).append(record)
    populations: list[tuple[str, list[Record]]] = [
        (OVERALL_GROUP, list(records))
    ]
    for name in sorted(groups):
        populations.append((name, groups[name]))
    return populations


def analyze_population(
    name: str, records: list[Record], query_days: tuple[int, ...]
) -> PopulationResult:
    day_events: dict[int, int] = {}
    day_censored: dict[int, int] = {}
    for record in records:
        bucket = day_events if record.event == 1 else day_censored
        bucket[record.days] = bucket.get(record.days, 0) + 1

    observed_days = sorted(set(day_events) | set(day_censored))
    subject_count = len(records)
    event_count = sum(day_events.values())
    censored_count = sum(day_censored.values())
    max_day = observed_days[-1]

    steps: list[StepRow] = []
    survival = 1.0
    median_day: int | None = None
    for day in observed_days:
        at_risk = sum(
            1 for record in records if record.days >= day
        )
        n_events = day_events.get(day, 0)
        n_censored = day_censored.get(day, 0)
        if n_events > 0:
            survival *= 1 - n_events / at_risk
        steps.append(
            StepRow(
                day=day,
                at_risk=at_risk,
                events=n_events,
                censored=n_censored,
                survival_after=survival,
            )
        )
        if (
            median_day is None
            and n_events > 0
            and survival <= 0.5
        ):
            median_day = day

    timepoints = tuple(
        _query_timepoint(day, records, observed_days, steps)
        for day in query_days
    )

    return PopulationResult(
        name=name,
        subject_count=subject_count,
        event_count=event_count,
        censored_count=censored_count,
        max_day=max_day,
        steps=tuple(steps),
        timepoints=timepoints,
        median_survival_days=median_day,
    )


def _query_timepoint(
    query_day: int,
    records: list[Record],
    observed_days: list[int],
    steps: list[StepRow],
) -> TimepointRow:
    at_risk = sum(1 for record in records if record.days >= query_day)

    if query_day > observed_days[-1]:
        return TimepointRow(
            query_day=query_day,
            at_risk=at_risk,
            survival=None,
            out_of_followup=True,
        )

    if query_day < observed_days[0]:
        survival = 1.0
    else:
        index = 0
        while index + 1 < len(observed_days) and observed_days[index + 1] <= query_day:
            index += 1
        survival = steps[index].survival_after

    return TimepointRow(
        query_day=query_day,
        at_risk=at_risk,
        survival=survival,
        out_of_followup=False,
    )
