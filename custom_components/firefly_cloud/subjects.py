"""Find a task's subject: Firefly tasks don't carry one.

A task names the classes it was set for (e.g. "Class PABC1 B"), and timetable
lessons start their description with the same class code alongside the subject,
so the two can be matched. Failing that, a "Subject: task" title gives the subject,
but only when it names a subject on the timetable, so titles like "Homework: …" or
"Hand in by 3:30pm" aren't mistaken for subjects.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

_YEAR_PREFIX = re.compile(r"^(year\s+)?\d+\s+")
_CLASS_PREFIX = re.compile(r"^class\s+", re.IGNORECASE)


def normalise(text: Any) -> str:
    """Lower-case and collapse whitespace, so codes and names compare loosely."""
    return " ".join(str(text or "").casefold().split())


def _without_year(name: str) -> str:
    """Drop a leading year from a normalised name, e.g. year 8 discovery → discovery."""
    return _YEAR_PREFIX.sub("", name)


def class_subjects(events: list[dict[str, Any]]) -> dict[str, str]:
    """Map normalised timetable class codes (the first line of a lesson's description) to their subject."""
    subjects: dict[str, str] = {}
    for event in events:
        code = normalise(str(event.get("description") or "").split("\n", 1)[0])
        if code and event.get("subject"):
            subjects.setdefault(code, event["subject"])
    return subjects


def title_subject(title: Any, timetable_subjects: Iterable[str]) -> str | None:
    """Return the timetable subject named by a "Subject: task" title, or None.

    "Discovery: Psych Lab" gives "Year 8 Discovery" when that's on the timetable.
    A leading year ("8 Discovery", "Year 8 Discovery") is ignored when comparing.
    """
    prefix, colon, _ = str(title or "").partition(":")
    wanted = _without_year(normalise(prefix))
    if not colon or not wanted:
        return None
    return next((s for s in timetable_subjects if _without_year(normalise(s)) == wanted), None)


def with_subjects(tasks: list[dict[str, Any]], by_class: dict[str, str]) -> list[dict[str, Any]]:
    """Return tasks with a subject where one can be found (raw tasks are left unchanged).

    ``by_class`` maps normalised class codes to timetable subjects (see class_subjects).
    Tasks that already have a subject are kept as they are. Otherwise the subject of
    the first class the task was set for is used, then a title prefix naming a
    timetable subject.
    """
    timetable_subjects = sorted(set(by_class.values()))
    result = []
    for task in tasks:
        if task.get("subject"):
            result.append(task)
            continue
        codes = (
            normalise(_CLASS_PREFIX.sub("", str(addressee.get("name") or "").strip()))
            for addressee in task.get("addressees") or []
            if isinstance(addressee, dict)
        )
        subject = next((by_class[code] for code in codes if code in by_class), None) or title_subject(
            task.get("title"), timetable_subjects
        )
        result.append({**task, "subject": subject} if subject else task)
    return result
