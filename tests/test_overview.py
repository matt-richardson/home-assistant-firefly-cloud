"""Tests for the child overview sent to the dashboard cards."""

from datetime import date, datetime, timedelta, timezone

import pytest

from custom_components.firefly_cloud.dates import local_midnight
from custom_components.firefly_cloud.overview import build_overview
from custom_components.firefly_cloud.task_changes import clear_change, observe_firefly_dates, set_change, task_record

TODAY = date(2026, 11, 14)
CHILD = "child-1"


@pytest.fixture(autouse=True)
def _melbourne(melbourne):
    """All overview tests run with HA in Australia/Melbourne."""


def _task(task_id, due, firefly_due=None, change=None, title=None, set_date=None):
    return {
        "id": task_id,
        "title": title or f"task {task_id}",
        "subject": "Design",
        "setter": "Ms Rivera",
        "set_date": set_date,
        "due_date": local_midnight(due) if due else None,
        "firefly_due_date": firefly_due if firefly_due is not None else due,
        "due_date_changed": False,
        "due_date_change_reason": None,
        "change": change,
    }


def _child(tasks=None, events=None):
    return {"tasks": {"all": tasks or []}, "events": {"week": events or []}}


def _event(start_utc, minutes, subject, location="M8"):
    start = datetime.fromisoformat(start_utc).replace(tzinfo=timezone.utc)
    return {"start": start, "end": start + timedelta(minutes=minutes), "subject": subject, "location": location}


def test_buckets_match_sensor_window():
    """Buckets follow the upcoming sensor's lookahead window."""
    tasks = [
        _task("a", date(2026, 11, 13)),
        _task("b", date(2026, 11, 14)),
        _task("c", date(2026, 11, 20)),
        _task("d", date(2026, 11, 21)),
        _task("e", None),
    ]
    overview = build_overview(_child(tasks), TODAY, 7)
    assert {t["id"]: t["bucket"] for t in overview["tasks"]} == {
        "a": "overdue",
        "b": "this_week",
        "c": "this_week",
        "d": "later",
        "e": "no_date",
    }
    assert overview["today"] == "2026-11-14"
    assert overview["lookahead_days"] == 7


def test_tasks_sorted_by_due_then_title():
    """Tasks are ordered by effective due date, then title; tasks without a date go last."""
    tasks = [
        _task("1", date(2026, 11, 20), title="Zebra"),
        _task("2", None, title="Aardvark"),
        _task("3", date(2026, 11, 20), title="Apple"),
        _task("4", date(2026, 11, 9), title="Late"),
    ]
    assert [t["title"] for t in build_overview(_child(tasks), TODAY, 7)["tasks"]] == [
        "Late",
        "Apple",
        "Zebra",
        "Aardvark",
    ]


def test_task_fields():
    """Each task carries ids as strings, both dates and the teacher."""
    [task] = build_overview(_child([_task(69040, date(2026, 11, 18), date(2026, 11, 11))]), TODAY, 7)["tasks"]
    assert task["id"] == "69040"
    assert task["due"] == "2026-11-18"
    assert task["firefly_due"] == "2026-11-11"
    assert task["subject"] == "Design"
    assert task["setter"] == "Ms Rivera"
    assert task["change"] is None
    assert task["school_change"] is None


def test_change_and_history_shape():
    """History lists school changes, undos and dashboard changes newest first, ending with when it was set."""
    state: dict = {}
    t0 = datetime(2026, 11, 10, 9, tzinfo=timezone.utc)
    observe_firefly_dates(state, CHILD, {"1": date(2026, 11, 11)}, t0)
    set_change(
        state,
        CHILD,
        "1",
        firefly_due=date(2026, 11, 11),
        new_due=date(2026, 11, 18),
        reason="Extended in class",
        now=t0 + timedelta(days=1),
    )
    clear_change(state, CHILD, "1", t0 + timedelta(days=2))
    observe_firefly_dates(state, CHILD, {"1": date(2026, 11, 13)}, t0 + timedelta(days=3))
    record = task_record(state, CHILD, "1")
    set_date = datetime(2026, 11, 2, 9, tzinfo=timezone.utc)

    [task] = build_overview(_child([_task("1", date(2026, 11, 13), change=record, set_date=set_date)]), TODAY, 7)[
        "tasks"
    ]

    assert [h["kind"] for h in task["history"]] == ["school", "undone", "dashboard", "set"]
    assert task["history"][0]["text_fields"] == {"from": "2026-11-11", "to": "2026-11-13"}
    assert task["history"][2]["text_fields"]["new_due_date"] == "2026-11-18"
    assert task["history"][2]["text_fields"]["reason"] == "Extended in class"
    assert task["history"][2]["text_fields"]["ended_by"] == "undone"
    assert task["history"][-1] == {
        "at": "2026-11-02T20:00:00+11:00",
        "kind": "set",
        "text_fields": {"setter": "Ms Rivera", "due": "2026-11-11"},
    }
    assert task["change"] is None
    assert task["school_change"] == {
        "from": "2026-11-11",
        "to": "2026-11-13",
        "seen_at": (t0 + timedelta(days=3)).isoformat(),
    }


def test_active_date_change():
    """An active date change is summarised for the card's tag."""
    state: dict = {}
    now = datetime(2026, 11, 12, 9, tzinfo=timezone.utc)
    set_change(
        state,
        CHILD,
        "1",
        firefly_due=date(2026, 11, 11),
        new_due=date(2026, 11, 18),
        reason="Extended in class",
        now=now,
    )
    [task] = build_overview(
        _child([_task("1", date(2026, 11, 18), date(2026, 11, 11), task_record(state, CHILD, "1"))]), TODAY, 7
    )["tasks"]
    assert task["change"] == {
        "kind": "date",
        "new_due_date": "2026-11-18",
        "reason": "Extended in class",
        "from": "2026-11-11",
        "changed_at": now.isoformat(),
        "confirmed": False,
    }
    assert task["history"][0]["kind"] == "dashboard"


def test_note_only_change_kind():
    """A reason without a date is a note."""
    state: dict = {}
    set_change(
        state,
        CHILD,
        "1",
        firefly_due=date(2026, 11, 11),
        new_due=None,
        reason="Doing it in class today",
        now=datetime(2026, 11, 14, tzinfo=timezone.utc),
    )
    [task] = build_overview(_child([_task("1", date(2026, 11, 11), change=task_record(state, CHILD, "1"))]), TODAY, 7)[
        "tasks"
    ]
    assert task["change"]["kind"] == "note"
    assert task["bucket"] == "overdue"
    assert task["history"][0]["kind"] == "note"


def test_history_without_set_date():
    """Without a set date, the 'set' entry has no time and stays last."""
    [task] = build_overview(_child([_task("1", date(2026, 11, 18))]), TODAY, 7)["tasks"]
    assert task["history"] == [{"at": None, "kind": "set", "text_fields": {"setter": "Ms Rivera", "due": "2026-11-18"}}]


def test_lesson_days_grouped_local():
    """Lessons are grouped by local date with local times, in start order."""
    events = [
        _event("2026-11-15T21:55:00", 60, "Year 8 German", "M7"),  # 08:55 Mon 16 Nov local
        _event("2026-11-15T21:40:00", 10, "Middle School Pastoral Program"),  # 08:40
    ]
    overview = build_overview(_child(events=events), TODAY, 7)
    assert overview["lesson_days"] == [
        {
            "date": "2026-11-16",
            "lessons": [
                {"start": "08:40", "end": "08:50", "subject": "Middle School Pastoral Program", "location": "M8"},
                {"start": "08:55", "end": "09:55", "subject": "Year 8 German", "location": "M7"},
            ],
        }
    ]


def test_lesson_days_limited_to_14_days():
    """Only the 14 days from today are included."""
    events = [
        _event("2026-11-13T22:00:00", 60, "Today"),  # 14 Nov local, included
        _event("2026-11-27T22:00:00", 60, "Day 14"),  # 28 Nov local, excluded
        _event("2026-11-26T22:00:00", 60, "Day 13"),  # 27 Nov local, included
        _event("2026-11-12T22:00:00", 60, "Yesterday"),  # 13 Nov local, excluded
    ]
    dates = [d["date"] for d in build_overview(_child(events=events), TODAY, 7)["lesson_days"]]
    assert dates == ["2026-11-14", "2026-11-27"]


def test_no_events_gives_empty_lesson_days():
    """No timetable gives no lesson days (the card shows its message)."""
    assert build_overview(_child(), TODAY, 7)["lesson_days"] == []


def test_missing_sections_tolerated():
    """A child with no tasks or events keys still builds."""
    assert build_overview({}, TODAY, 7) == {"today": "2026-11-14", "lookahead_days": 7, "tasks": [], "lesson_days": []}


def test_confirmed_change_marked():
    """A change the school confirmed says so in the summary and history."""
    state: dict = {}
    now = datetime(2026, 11, 12, 9, tzinfo=timezone.utc)
    observe_firefly_dates(state, CHILD, {"1": date(2026, 11, 11)}, now)
    set_change(state, CHILD, "1", firefly_due=date(2026, 11, 11), new_due=date(2026, 11, 18), reason=None, now=now)
    observe_firefly_dates(state, CHILD, {"1": date(2026, 11, 18)}, now + timedelta(hours=1))
    [task] = build_overview(_child([_task("1", date(2026, 11, 18), change=task_record(state, CHILD, "1"))]), TODAY, 7)[
        "tasks"
    ]
    assert task["change"]["confirmed"] is True
    assert [h["kind"] for h in task["history"]] == ["school", "dashboard", "set"]
    assert task["history"][1]["text_fields"]["confirmed"] is True


def test_set_date_in_local_time():
    """The 'set' entry is in local time, so the date shown is the local day."""
    set_date = datetime(2026, 11, 1, 22, tzinfo=timezone.utc)  # 9am on 2 Nov in Melbourne
    [task] = build_overview(_child([_task("1", date(2026, 11, 18), set_date=set_date)]), TODAY, 7)["tasks"]
    assert task["history"][-1]["at"] == "2026-11-02T09:00:00+11:00"


def test_lesson_crossing_midnight_ends_at_24_00():
    """A lesson that ends on a later day is sent as ending at 24:00, so it isn't treated as already over."""
    events = [_event("2026-11-16T12:00:00", 90, "Overnight Camp")]  # 23:00 Mon 16 Nov to 00:30 Tue (Melbourne)
    [day] = build_overview(_child(events=events), TODAY, 7)["lesson_days"]
    assert day["date"] == "2026-11-16"
    assert day["lessons"][0]["start"] == "23:00"
    assert day["lessons"][0]["end"] == "24:00"


def test_unknown_subject_sent_as_none():
    """The card gets no subject rather than the placeholder "Unknown Subject"."""
    task = _task("1", date(2026, 11, 18)) | {"subject": "Unknown Subject"}
    [overview_task] = build_overview(_child([task]), TODAY, 7)["tasks"]
    assert overview_task["subject"] is None
