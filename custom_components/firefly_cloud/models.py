"""Typed Firefly data: tasks, lessons, children and the shared due-date buckets."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Any

from homeassistant.util import dt as dt_util

from .dates import parse_due_date

UNKNOWN_SUBJECT = "Unknown Subject"


def firefly_task_id(task: dict[str, Any]) -> Any:
    """Return a task's Firefly id (as used for todo items and dashboard changes)."""
    return task.get("guid", task.get("id", "unknown"))


class Bucket(StrEnum):
    """Where a due date falls relative to today."""

    OVERDUE = "overdue"
    THIS_WEEK = "this_week"
    LATER = "later"
    NO_DATE = "no_date"


def bucket(due: date | None, today: date, lookahead_days: float) -> Bucket:
    """Return the bucket for a due date: this week is [today, today + lookahead_days)."""
    if due is None:
        return Bucket.NO_DATE
    if due < today:
        return Bucket.OVERDUE
    if due < today + timedelta(days=lookahead_days):
        return Bucket.THIS_WEEK
    return Bucket.LATER


def _parse_datetime(value: str) -> datetime:
    """Parse an ISO time (``Z`` allowed); a time without a timezone is Home Assistant local."""
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return dt_util.as_local(parsed)
    return parsed


@dataclass(frozen=True, slots=True)
class Lesson:
    """A timetabled class."""

    start: datetime
    end: datetime
    subject: str
    location: str | None
    description: str | None
    guild: str | None
    attendees: tuple[Any, ...]

    @classmethod
    def from_firefly(cls, event: dict[str, Any]) -> Lesson:
        """Build a lesson from a Firefly event.

        Raises:
            KeyError: the event has no start or end.
            ValueError: the start or end isn't an ISO time.
        """
        return cls(
            start=_parse_datetime(event["start"]),
            end=_parse_datetime(event["end"]),
            subject=event.get("subject", UNKNOWN_SUBJECT),
            location=event.get("location"),
            description=event.get("description"),
            guild=event.get("guild"),
            attendees=tuple(event.get("attendees") or ()),
        )


@dataclass(frozen=True, slots=True)
class Task:  # pylint: disable=too-many-instance-attributes
    """A homework task; ``due`` is the date in force and ``firefly_due`` is the school's."""

    id: str
    title: str
    description: str
    subject: str | None
    setter: Any
    set_at: datetime | None
    completion_status: str
    firefly_due: date | None
    due: date | None
    change: dict[str, Any] | None = None

    @classmethod
    def from_firefly(cls, raw: dict[str, Any]) -> Task:
        """Build a task from Firefly's data, with no dashboard change applied."""
        subject_data = raw.get("subject")
        subject: str | None = None
        if isinstance(subject_data, dict):
            subject = subject_data.get("name", UNKNOWN_SUBJECT)
        elif isinstance(subject_data, str):
            subject = subject_data

        setter = raw.get("setter", "Unknown")
        if isinstance(setter, dict):
            setter = setter.get("name", "Unknown")

        set_at = None
        if raw.get("setDate"):
            try:
                set_at = datetime.fromisoformat(raw["setDate"].replace("Z", "+00:00"))
            except (ValueError, TypeError, AttributeError):
                set_at = None

        firefly_due = parse_due_date(raw.get("dueDate"))
        return cls(
            id=str(firefly_task_id(raw)),
            title=raw.get("title", "Untitled Task"),
            description=raw.get("description", ""),
            subject=subject,
            setter=setter,
            set_at=set_at,
            completion_status=raw.get("completionStatus", "Unknown"),
            firefly_due=firefly_due,
            due=firefly_due,
        )

    @property
    def is_completed(self) -> bool:
        """Whether Firefly marks the task completed."""
        return (self.completion_status or "").lower() == "completed"

    @property
    def _active_change(self) -> dict[str, Any]:
        return (self.change or {}).get("active") or {}

    @property
    def due_date_changed(self) -> bool:
        """Whether a dashboard change moved the due date."""
        return bool(self._active_change.get("new_due_date"))

    @property
    def change_reason(self) -> str | None:
        """The reason given for the active dashboard change, if any."""
        return self._active_change.get("reason")


@dataclass(frozen=True)
class ChildData:
    """One child's tasks and lessons, bucketed relative to ``today``."""

    guid: str
    name: str | None
    tasks: tuple[Task, ...]
    lessons: tuple[Lesson, ...]
    today: date
    lookahead_days: float

    @property
    def upcoming(self) -> list[Task]:
        """Tasks due from today up to the lookahead."""
        return [t for t in self.tasks if bucket(t.due, self.today, self.lookahead_days) is Bucket.THIS_WEEK]

    @property
    def overdue(self) -> list[Task]:
        """Uncompleted tasks due before today."""
        return [
            t
            for t in self.tasks
            if bucket(t.due, self.today, self.lookahead_days) is Bucket.OVERDUE and not t.is_completed
        ]

    @property
    def due_today(self) -> list[Task]:
        """Tasks due today."""
        return [t for t in self.tasks if t.due == self.today]


@dataclass(frozen=True)
class FireflyData:
    """Everything the coordinator fetched."""

    children: dict[str, ChildData]
    user_info: dict[str, Any]
    last_updated: datetime

    def child(self, guid: str) -> ChildData | None:
        """Return a child's data, or None if unknown."""
        return self.children.get(guid)
