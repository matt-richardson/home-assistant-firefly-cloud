"""Tests for the typed Firefly models."""

from dataclasses import replace
from datetime import date, datetime, timezone

import pytest
from conftest import make_child, make_data

from custom_components.firefly_cloud.models import UNKNOWN_SUBJECT, Bucket, Lesson, Task, bucket

TODAY = date(2026, 11, 14)


def test_bucket_edges():
    assert bucket(None, TODAY, 7) is Bucket.NO_DATE
    assert bucket(date(2026, 11, 13), TODAY, 7) is Bucket.OVERDUE
    assert bucket(date(2026, 11, 14), TODAY, 7) is Bucket.THIS_WEEK
    assert bucket(date(2026, 11, 20), TODAY, 7) is Bucket.THIS_WEEK
    assert bucket(date(2026, 11, 21), TODAY, 7) is Bucket.LATER


def test_bucket_accepts_float_lookahead():
    assert bucket(date(2026, 11, 20), TODAY, 7.0) is Bucket.THIS_WEEK
    assert bucket(date(2026, 11, 21), TODAY, 7.0) is Bucket.LATER


def test_task_from_firefly_matches_processed_rules():
    assert Task.from_firefly({"guid": 42}).id == "42"
    assert Task.from_firefly({"id": 7}).id == "7"
    assert Task.from_firefly({}).id == "unknown"
    empty = Task.from_firefly({})
    assert empty.title == "Untitled Task"
    assert empty.description == ""
    assert empty.subject is None
    assert empty.setter == "Unknown"
    assert empty.set_at is None
    assert empty.completion_status == "Unknown"
    assert empty.change is None
    assert Task.from_firefly({"title": "Essay", "description": "d"}).title == "Essay"
    assert Task.from_firefly({"description": "d"}).description == "d"
    assert Task.from_firefly({"setter": None}).setter is None
    assert Task.from_firefly({"setter": {"name": "Ms Rivera"}}).setter == "Ms Rivera"
    assert Task.from_firefly({"setter": {}}).setter == "Unknown"
    assert Task.from_firefly({"setter": "Mr Lee"}).setter == "Mr Lee"
    assert Task.from_firefly({"subject": {"name": "Art"}}).subject == "Art"
    assert Task.from_firefly({"subject": {}}).subject is None
    assert Task.from_firefly({"subject": "Music"}).subject == "Music"
    assert Task.from_firefly({"subject": None}).subject is None
    assert Task.from_firefly({"subject": 5}).subject is None
    assert Task.from_firefly({"completionStatus": "Done"}).completion_status == "Done"


def test_task_set_at_parsing():
    assert Task.from_firefly({"setDate": "2026-11-01T00:00:00Z"}).set_at == datetime(2026, 11, 1, tzinfo=timezone.utc)
    assert Task.from_firefly({"setDate": "garbage"}).set_at is None
    assert Task.from_firefly({"setDate": 5}).set_at is None


@pytest.mark.parametrize("raw", [{"dueDate": None}, {"dueDate": "not a date"}, {}])
def test_task_without_due_date_has_no_bucket_date(raw):
    task = Task.from_firefly(raw)
    assert task.due is None and task.firefly_due is None


def test_task_due_date_is_local_calendar_date(melbourne):
    task = Task.from_firefly({"dueDate": "2026-11-20T00:00:00"})
    assert task.due == date(2026, 11, 20)
    assert task.firefly_due == date(2026, 11, 20)


def test_task_change_properties():
    plain = Task.from_firefly({"completionStatus": "Completed"})
    assert plain.is_completed
    assert not plain.due_date_changed
    assert plain.change_reason is None
    assert Task.from_firefly({"completionStatus": None}).is_completed is False

    moved = replace(plain, change={"active": {"new_due_date": "2026-11-22", "reason": "Away"}})
    assert moved.due_date_changed
    assert moved.change_reason == "Away"
    note = replace(plain, change={"active": {"new_due_date": None, "reason": "Note"}})
    assert not note.due_date_changed
    assert note.change_reason == "Note"
    assert replace(plain, change={"active": None}).change_reason is None


def test_lesson_without_timezone_is_local(melbourne):
    lesson = Lesson.from_firefly({"start": "2026-11-16T09:00:00", "end": "2026-11-16T10:00:00"})
    assert lesson.start.tzinfo is not None
    assert lesson.start.hour == 9
    assert lesson.end.hour == 10


def test_lesson_defaults(melbourne):
    lesson = Lesson.from_firefly({"start": "2026-11-16T09:00:00Z", "end": "2026-11-16T10:00:00Z"})
    assert lesson.subject == UNKNOWN_SUBJECT
    assert lesson.attendees == ()
    assert lesson.location is None and lesson.description is None and lesson.guild is None
    assert lesson.start == datetime(2026, 11, 16, 9, tzinfo=timezone.utc)
    full = Lesson.from_firefly(
        {
            "start": "2026-11-16T09:00:00Z",
            "end": "2026-11-16T10:00:00Z",
            "subject": "Art",
            "location": "A1",
            "description": "d",
            "guild": "g",
            "attendees": [{"name": "x"}],
        }
    )
    assert (full.subject, full.location, full.description, full.guild) == ("Art", "A1", "d", "g")
    assert full.attendees == ({"name": "x"},)


def test_lesson_invalid_raises():
    with pytest.raises(KeyError):
        Lesson.from_firefly({"start": "2026-11-16T09:00:00"})
    with pytest.raises(ValueError):
        Lesson.from_firefly({"start": "x", "end": "y"})


def test_child_lists_follow_buckets():
    def raw(guid, due, status="Todo"):
        return Task.from_firefly({"guid": guid, "dueDate": f"{due}T00:00:00", "completionStatus": status})

    tasks = [
        raw("a", "2026-11-13"),
        raw("b", "2026-11-13", "Completed"),
        raw("c", "2026-11-14"),
        raw("d", "2026-11-20"),
        raw("e", "2026-11-21"),
        Task.from_firefly({"guid": "f"}),
    ]
    child = make_child(tasks=tasks, today=TODAY)
    assert [t.id for t in child.overdue] == ["a"]
    assert [t.id for t in child.upcoming] == ["c", "d"]
    assert [t.id for t in child.due_today] == ["c"]


def test_firefly_data_child():
    child = make_child(today=TODAY)
    data = make_data(child)
    assert data.child("child-1") is child
    assert data.child("nope") is None
