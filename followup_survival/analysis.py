"""Kaplan-Meier ladder computation, time-point queries and summaries."""

from dataclasses import dataclass

from .validation import Record

OVERALL = "overall"


@dataclass(frozen=True)
class Step:
    days: int
    at_risk: int
    events: int
    censored: int
    survival: float


@dataclass(frozen=True)
class TimePoint:
    days: int
    at_risk: int
    survival: float | None
    out_of_followup: bool


@dataclass(frozen=True)
class GroupResult:
    name: str
    n: int
    events: int
    censored: int
    steps: list[Step]
    median_days: int | None


def aggregate(records: list[Record], group: str | None = None) -> GroupResult:
    """Build the KM ladder for one group (or the overall population)."""
    members = records if group is None else [r for r in records if r.group == group]
    n = len(members)
    total_events = sum(r.event for r in members)

    day_events: dict[int, int] = {}
    day_censored: dict[int, int] = {}
    for rec in members:
        if rec.event == 1:
            day_events[rec.days] = day_events.get(rec.days, 0) + 1
        else:
            day_censored[rec.days] = day_censored.get(rec.days, 0) + 1

    steps: list[Step] = []
    survival = 1.0
    for day in sorted(set(day_events) | set(day_censored)):
        events = day_events.get(day, 0)
        censored = day_censored.get(day, 0)
        at_risk = sum(1 for rec in members if rec.days >= day)
        if events > 0:
            survival *= 1.0 - events / at_risk
            if survival == 0.0:
                survival = 0.0
        steps.append(
            Step(
                days=day,
                at_risk=at_risk,
                events=events,
                censored=censored,
                survival=round(survival, 12),
            )
        )

    median_days = None
    for step in steps:
        if step.events > 0 and step.survival <= 0.5:
            median_days = step.days
            break

    return GroupResult(
        name=OVERALL if group is None else group,
        n=n,
        events=total_events,
        censored=n - total_events,
        steps=steps,
        median_days=median_days,
    )


def analyze_all(records: list[Record]) -> list[GroupResult]:
    """Overall result first, then real groups sorted by name."""
    results = [aggregate(records)]
    groups = sorted({r.group for r in records})
    results.extend(aggregate(records, g) for g in groups)
    return results


def query_at(result: GroupResult, day: int) -> TimePoint:
    """Survival and at-risk count at a queried day."""
    at_risk = _at_risk_count(result, day)
    if not result.steps or day < result.steps[0].days:
        return TimePoint(day, at_risk, 1.0, False)
    if day > result.steps[-1].days:
        return TimePoint(day, at_risk, None, True)

    current = 1.0
    for step in result.steps:
        if step.days <= day:
            current = step.survival
        else:
            break
    return TimePoint(day, at_risk, current, False)


def _at_risk_count(result: GroupResult, day: int) -> int:
    """Objects whose follow-up ends on or after ``day``."""
    removed_before = 0
    for step in result.steps:
        if step.days < day:
            removed_before += step.events + step.censored
        else:
            break
    return result.n - removed_before
