"""The child overview sent to the dashboard cards over the websocket.

This is the cards' whole data contract: every open task (with its bucket, dates,
dashboard change, latest school change and history) and the lessons for the next
14 days. It's built only from coordinator data, so it never calls Firefly.
"""

from __future__ import annotations

from datetime import date, datetime, timedelta
from typing import Any

from homeassistant.util import dt as dt_util

LESSON_DAYS = 14
# The coordinator's placeholder when a task's subject can't be found; the card shows no subject instead
UNKNOWN_SUBJECT = "Unknown Subject"

BUCKET_OVERDUE = "overdue"
BUCKET_THIS_WEEK = "this_week"
BUCKET_LATER = "later"
BUCKET_NO_DATE = "no_date"


def _iso(day: date | None) -> str | None:
    return day.isoformat() if day else None


def _bucket(due: date | None, today: date, lookahead_days: int) -> str:
    if due is None:
        return BUCKET_NO_DATE
    if due < today:
        return BUCKET_OVERDUE
    if due < today + timedelta(days=lookahead_days):
        return BUCKET_THIS_WEEK
    return BUCKET_LATER


def _change_summary(active: dict[str, Any] | None) -> dict[str, Any] | None:
    if not active:
        return None
    return {
        "kind": "date" if active["new_due_date"] else "note",
        "new_due_date": active["new_due_date"],
        "reason": active["reason"],
        "from": active["firefly_due_at_change"],
        "changed_at": active["changed_at"],
        "confirmed": active["confirmed"],
    }


def _change_entry(change: dict[str, Any]) -> dict[str, Any]:
    fields = {
        "new_due_date": change["new_due_date"],
        "from": change["firefly_due_at_change"],
        "reason": change["reason"],
    }
    if change.get("confirmed"):
        fields["confirmed"] = True
    if "ended_by" in change:
        fields["ended_by"] = change["ended_by"]
    return {
        "at": change["changed_at"],
        "kind": "dashboard" if change["new_due_date"] else "note",
        "text_fields": fields,
    }


def _history(task: dict[str, Any], record: dict[str, Any] | None, firefly_due: date | None) -> list[dict[str, Any]]:
    """Newest first: dashboard changes and notes, undos, school changes; then when it was set."""
    entries: list[dict[str, Any]] = []
    first_due = _iso(firefly_due)
    if record:
        for change in record["ended"]:
            entries.append(_change_entry(change))
            if change["ended_by"] == "undone":
                entries.append(
                    {
                        "at": change["ended_at"],
                        "kind": "undone",
                        "text_fields": {"new_due_date": change["new_due_date"], "reason": change["reason"]},
                    }
                )
        if record["active"]:
            entries.append(_change_entry(record["active"]))
        for school in record["school_changes"]:
            entries.append(
                {"at": school["seen_at"], "kind": "school", "text_fields": {"from": school["from"], "to": school["to"]}}
            )
        if record["school_changes"]:
            first_due = record["school_changes"][0]["from"]
    entries.sort(key=lambda entry: datetime.fromisoformat(entry["at"]), reverse=True)

    set_date = task.get("set_date")
    entries.append(
        {
            "at": dt_util.as_local(set_date).isoformat() if set_date else None,
            "kind": "set",
            "text_fields": {"setter": task.get("setter"), "due": first_due},
        }
    )
    return entries


def _task_overview(task: dict[str, Any], today: date, lookahead_days: int) -> dict[str, Any]:
    due = task["due_date"].date() if task.get("due_date") else None
    firefly_due = task.get("firefly_due_date", due)
    record = task.get("change")
    school_changes = (record or {}).get("school_changes") or []
    return {
        "id": str(task["id"]),
        "title": task.get("title"),
        "subject": None if task.get("subject") in (None, UNKNOWN_SUBJECT) else task["subject"],
        "setter": task.get("setter"),
        "due": _iso(due),
        "firefly_due": _iso(firefly_due),
        "bucket": _bucket(due, today, lookahead_days),
        "change": _change_summary((record or {}).get("active")),
        "school_change": school_changes[-1] if school_changes else None,
        "history": _history(task, record, firefly_due),
    }


def _end_time(start: datetime, end: datetime) -> str:
    """HH:MM end time; a lesson running past midnight ends at "24:00" on its start day."""
    return "24:00" if end.date() > start.date() else end.strftime("%H:%M")


def _lesson_days(events: list[dict[str, Any]], today: date) -> list[dict[str, Any]]:
    end = today + timedelta(days=LESSON_DAYS)
    days: dict[str, list[dict[str, Any]]] = {}
    for event in sorted(events, key=lambda e: e["start"]):
        start = dt_util.as_local(event["start"])
        if not today <= start.date() < end:
            continue
        days.setdefault(start.date().isoformat(), []).append(
            {
                "start": start.strftime("%H:%M"),
                "end": _end_time(start, dt_util.as_local(event["end"])),
                "subject": event.get("subject"),
                "location": event.get("location"),
            }
        )
    return [{"date": day, "lessons": lessons} for day, lessons in sorted(days.items())]


def build_overview(child_data: dict[str, Any], today: date, lookahead_days: int) -> dict[str, Any]:
    """Build the tasks and lessons overview for one child, for the dashboard cards."""
    tasks = [_task_overview(task, today, lookahead_days) for task in child_data.get("tasks", {}).get("all", [])]
    tasks.sort(key=lambda t: (t["due"] is None, t["due"] or "", t["title"] or ""))
    return {
        "today": today.isoformat(),
        "lookahead_days": lookahead_days,
        "tasks": tasks,
        "lesson_days": _lesson_days(child_data.get("events", {}).get("week", []), today),
    }
