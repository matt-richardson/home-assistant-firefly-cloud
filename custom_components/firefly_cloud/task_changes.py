"""Due date changes made on the dashboard, and changes the school made in Firefly.

Firefly's due date can't be changed from here, so a change made on the dashboard is
kept in Home Assistant and applied on top of Firefly's date. The rules are pure
functions over a JSON-able state, so they can be tested without Home Assistant:

    {child_guid: {task_id: {
        "last_firefly_due": "YYYY-MM-DD" | None,   # Firefly's date when last seen
        "active": Change | None,                   # the change in force, if any
        "ended": [Change + ended_at/ended_by],     # history of earlier changes
        "school_changes": [{"from", "to", "seen_at"}],
    }}}

A Change is {"new_due_date", "reason", "firefly_due_at_change", "changed_at",
"confirmed"}; a note is a change with no new_due_date. The school's date wins: when
Firefly's date moves, the active change ends, unless the school moved it to the same
date, which confirms it.
"""

from __future__ import annotations

from dataclasses import replace
from datetime import date, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

from .const import DOMAIN
from .models import Task

STORAGE_VERSION = 1
STORAGE_KEY = f"{DOMAIN}.task_changes.{{entry_id}}"

ENDED_UNDONE = "undone"
ENDED_SCHOOL_CHANGED = "school_changed"
ENDED_REPLACED = "replaced"


def _iso(day: date | None) -> str | None:
    return day.isoformat() if day else None


def _new_record(firefly_due: date | None) -> dict[str, Any]:
    return {"last_firefly_due": _iso(firefly_due), "active": None, "ended": [], "school_changes": []}


def _end_active(record: dict[str, Any], ended_by: str, now: datetime) -> None:
    record["ended"].append({**record["active"], "ended_at": now.isoformat(), "ended_by": ended_by})
    record["active"] = None


def task_record(state: dict[str, Any], child_guid: str, task_id: Any) -> dict[str, Any] | None:
    """Return the stored record for a task, or None."""
    return state.get(child_guid, {}).get(str(task_id))


def observe_firefly_dates(
    state: dict[str, Any], child_guid: str, firefly_dues: dict[str, date | None], now: datetime
) -> bool:
    """Record Firefly's current due dates for a child's open tasks; return whether state changed.

    New tasks get a baseline (no school change). A changed date is logged as a school
    change and ends the active dashboard change, or confirms it if the dates now match.
    Tasks that are no longer open are dropped.
    """
    dues = {str(task_id): _iso(due) for task_id, due in firefly_dues.items()}
    records = state.setdefault(child_guid, {})
    changed = False

    for task_id in [tid for tid in records if tid not in dues]:
        del records[task_id]
        changed = True

    for task_id, due in dues.items():
        record = records.get(task_id)
        if record is None:
            records[task_id] = {**_new_record(None), "last_firefly_due": due}
            changed = True
            continue
        if record["last_firefly_due"] == due:
            continue
        record["school_changes"].append({"from": record["last_firefly_due"], "to": due, "seen_at": now.isoformat()})
        record["last_firefly_due"] = due
        active = record["active"]
        if active is not None:
            if active["new_due_date"] is not None and active["new_due_date"] == due:
                active["confirmed"] = True
            else:
                _end_active(record, ENDED_SCHOOL_CHANGED, now)
        changed = True

    if not records:
        del state[child_guid]
    return changed


def set_change(
    state: dict[str, Any],
    child_guid: str,
    task_id: Any,
    *,
    firefly_due: date | None,
    new_due: date | None,
    reason: str | None,
    now: datetime,
) -> None:
    """Make a dashboard change: a new due date, a note (reason only), or both.

    Raises:
        ValueError: "nothing_to_change" if there's neither a new date nor a reason.
    """
    reason = (reason or "").strip() or None
    if new_due is not None and new_due == firefly_due:
        # A "move" to Firefly's own date is no move: with a reason it's a note,
        # without one it puts a moved task back (undo)
        new_due = None
        existing = task_record(state, child_guid, task_id)
        if reason is None and existing is not None and existing["active"] is not None:
            _end_active(existing, ENDED_UNDONE, now)
            return
    if new_due is None and reason is None:
        raise ValueError("nothing_to_change")
    records = state.setdefault(child_guid, {})
    record = records.setdefault(str(task_id), _new_record(firefly_due))
    if record["active"] is not None:
        _end_active(record, ENDED_REPLACED, now)
    record["active"] = {
        "new_due_date": _iso(new_due),
        "reason": reason,
        "firefly_due_at_change": _iso(firefly_due),
        "changed_at": now.isoformat(),
        "confirmed": False,
    }


def clear_change(state: dict[str, Any], child_guid: str, task_id: Any, now: datetime) -> None:
    """Undo the active dashboard change, keeping it in the history.

    Raises:
        ValueError: "no_change" if the task has no active change.
    """
    record = task_record(state, child_guid, task_id)
    if record is None or record["active"] is None:
        raise ValueError("no_change")
    _end_active(record, ENDED_UNDONE, now)


def effective_due(state: dict[str, Any], child_guid: str, task_id: Any, firefly_due: date | None) -> date | None:
    """Return the due date in force: the dashboard date if one is active, else Firefly's."""
    record = task_record(state, child_guid, task_id)
    if record and record["active"] and record["active"]["new_due_date"]:
        return date.fromisoformat(record["active"]["new_due_date"])
    return firefly_due


def apply_changes(
    change_store: TaskChangeStore | None, child_guid: str, tasks: list[Task], now: datetime
) -> list[Task]:
    """Record Firefly's dates for a child's tasks and return them with the date in force applied.

    Each returned task keeps Firefly's own date in ``firefly_due``, has the date in force
    in ``due`` and carries its change record in ``change``. The store is saved only if
    Firefly's dates changed. With no store the tasks are returned as they are.
    """
    if change_store is None:
        return tasks
    state = change_store.state
    if observe_firefly_dates(state, child_guid, {task.id: task.firefly_due for task in tasks}, now):
        change_store.async_save_delayed()
    return [
        replace(
            task,
            due=effective_due(state, child_guid, task.id, task.firefly_due),
            change=task_record(state, child_guid, task.id),
        )
        for task in tasks
    ]


class TaskChangeStore:
    """Persists one config entry's task changes in Home Assistant's storage."""

    def __init__(self, hass: HomeAssistant, entry_id: str) -> None:
        """Create the store for a config entry."""
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY.format(entry_id=entry_id))
        self._state: dict[str, Any] = {}
        self._class_subjects: dict[str, dict[str, str]] = {}
        self._save_pending = False
        self._closed = False

    @property
    def state(self) -> dict[str, Any]:
        """The current state (mutated in place by the rule functions)."""
        return self._state

    async def async_load(self) -> None:
        """Load saved changes and class subjects, starting empty if there are none."""
        data = await self._store.async_load() or {}
        self._state = data.get("tasks", {})
        self._class_subjects = data.get("class_subjects", {})

    def remember_class_subjects(self, child_guid: str, fresh: dict[str, str]) -> dict[str, str]:
        """Merge the timetable's class subjects into those remembered for a child, and return them all.

        Remembering them keeps subjects through holidays, when the timetable is empty.
        A code seen again with a different subject takes the new one. Saved only on change.
        """
        known = self._class_subjects.get(child_guid, {})
        merged = {**known, **fresh}
        if merged != known:
            self._class_subjects[child_guid] = merged
            self.async_save_delayed()
        return merged

    def async_save_delayed(self) -> None:
        """Save the state shortly, coalescing bursts of changes."""
        if self._closed:
            # Unloaded: a late save from an update still running must not overwrite a
            # reloaded entry's saves or recreate a removed entry's file
            return
        self._save_pending = True
        self._store.async_delay_save(self._data_to_save, 1)

    def _data_to_save(self) -> dict[str, Any]:
        self._save_pending = False
        return {"tasks": self._state, "class_subjects": self._class_subjects}

    async def async_flush(self) -> None:
        """Write a pending save now and stop saving (on unload), so a reload or removal can't lose or resurrect it."""
        self._closed = True
        if self._save_pending:
            self._save_pending = False
            await self._store.async_save(self._data_to_save())

    async def async_remove(self) -> None:
        """Delete the saved state (the config entry was removed)."""
        await self._store.async_remove()
