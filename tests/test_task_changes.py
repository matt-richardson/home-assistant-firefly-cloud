"""Tests for the task change rules and their store."""

from datetime import date, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from zoneinfo import ZoneInfo

import pytest
from conftest import make_task

from custom_components.firefly_cloud.task_changes import (
    TaskChangeStore,
    apply_changes,
    clear_change,
    effective_due,
    observe_firefly_dates,
    set_change,
    task_record,
)

MEL = ZoneInfo("Australia/Melbourne")
NOW = datetime(2026, 11, 14, 9, tzinfo=MEL)
CHILD = "child-1"
TASK = "69040"
NOV = {d: date(2026, 11, d) for d in range(1, 31)}


def _observed(due):
    """State with TASK seen once at the given Firefly due date."""
    state: dict = {}
    observe_firefly_dates(state, CHILD, {TASK: due}, NOW)
    return state


def test_first_observation_is_baseline():
    """The first time a task is seen, its date is recorded and no school change is logged."""
    state: dict = {}
    assert observe_firefly_dates(state, CHILD, {TASK: NOV[11]}, NOW) is True
    record = task_record(state, CHILD, TASK)
    assert record["school_changes"] == []
    assert record["last_firefly_due"] == "2026-11-11"
    assert observe_firefly_dates(state, CHILD, {TASK: NOV[11]}, NOW) is False


def test_school_change_recorded():
    """A change to Firefly's own date is logged as a school change."""
    state = _observed(NOV[11])
    assert observe_firefly_dates(state, CHILD, {TASK: NOV[13]}, NOW) is True
    record = task_record(state, CHILD, TASK)
    assert record["school_changes"] == [{"from": "2026-11-11", "to": "2026-11-13", "seen_at": NOW.isoformat()}]
    assert record["last_firefly_due"] == "2026-11-13"


def test_school_change_ends_active_change():
    """The school's date wins over a dashboard change."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[18], reason="Extended in class", now=NOW)
    later = NOW + timedelta(days=1)
    observe_firefly_dates(state, CHILD, {TASK: NOV[20]}, later)
    record = task_record(state, CHILD, TASK)
    assert record["active"] is None
    assert record["ended"][-1]["ended_by"] == "school_changed"
    assert record["ended"][-1]["ended_at"] == later.isoformat()
    assert effective_due(state, CHILD, TASK, NOV[20]) == NOV[20]


def test_school_change_to_same_date_confirms():
    """When Firefly moves to the dashboard date, the change is confirmed, not ended."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[18], reason=None, now=NOW)
    observe_firefly_dates(state, CHILD, {TASK: NOV[18]}, NOW)
    record = task_record(state, CHILD, TASK)
    assert record["active"]["confirmed"] is True
    assert record["ended"] == []


def test_school_change_ends_note_only_change():
    """A note-only change also ends when the school changes the date."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=None, reason="Doing it in class today", now=NOW)
    observe_firefly_dates(state, CHILD, {TASK: NOV[12]}, NOW)
    assert task_record(state, CHILD, TASK)["ended"][-1]["ended_by"] == "school_changed"


def test_missing_task_removed():
    """Tasks no longer returned by Firefly (submitted or deleted) are dropped."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[18], reason=None, now=NOW)
    assert observe_firefly_dates(state, CHILD, {}, NOW) is True
    assert task_record(state, CHILD, TASK) is None


def test_other_children_untouched():
    """Observing one child doesn't touch another child's records."""
    state = _observed(NOV[11])
    observe_firefly_dates(state, "child-2", {}, NOW)
    assert task_record(state, CHILD, TASK) is not None


def test_set_change_records_fields():
    """A date change stores the new date, reason, Firefly's date and when."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[18], reason="  Extended in class ", now=NOW)
    assert task_record(state, CHILD, TASK)["active"] == {
        "new_due_date": "2026-11-18",
        "reason": "Extended in class",
        "firefly_due_at_change": "2026-11-11",
        "changed_at": NOW.isoformat(),
        "confirmed": False,
    }
    assert effective_due(state, CHILD, TASK, NOV[11]) == NOV[18]


def test_set_change_replaces_previous():
    """A newer change ends the previous one as replaced."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[18], reason=None, now=NOW)
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[19], reason=None, now=NOW)
    record = task_record(state, CHILD, TASK)
    assert record["ended"][-1]["ended_by"] == "replaced"
    assert record["ended"][-1]["new_due_date"] == "2026-11-18"
    assert record["active"]["new_due_date"] == "2026-11-19"


def test_note_only_keeps_firefly_date():
    """A reason without a date is a note and leaves the due date alone."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=None, reason="Doing it in class today", now=NOW)
    assert task_record(state, CHILD, TASK)["active"]["new_due_date"] is None
    assert effective_due(state, CHILD, TASK, NOV[11]) == NOV[11]


@pytest.mark.parametrize("reason", [None, "", "  "])
def test_set_change_requires_date_or_reason(reason):
    """There must be a new date or a non-blank reason."""
    state = _observed(NOV[11])
    with pytest.raises(ValueError, match="nothing_to_change"):
        set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=None, reason=reason, now=NOW)


def test_set_change_on_unseen_task():
    """A change for a task not yet observed starts its record from Firefly's date."""
    state: dict = {}
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[18], reason=None, now=NOW)
    assert task_record(state, CHILD, TASK)["last_firefly_due"] == "2026-11-11"
    assert observe_firefly_dates(state, CHILD, {TASK: NOV[11]}, NOW) is False


def test_clear_change_logs_undo():
    """Undo ends the change and keeps it in the history."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[18], reason=None, now=NOW)
    clear_change(state, CHILD, TASK, NOW)
    record = task_record(state, CHILD, TASK)
    assert record["active"] is None
    assert record["ended"][-1]["ended_by"] == "undone"
    assert effective_due(state, CHILD, TASK, NOV[11]) == NOV[11]


def test_clear_without_change_raises():
    """Undo with nothing to undo is an error."""
    with pytest.raises(ValueError, match="no_change"):
        clear_change(_observed(NOV[11]), CHILD, TASK, NOW)
    with pytest.raises(ValueError, match="no_change"):
        clear_change({}, CHILD, TASK, NOW)


def test_effective_due_without_record():
    """With no record, the effective date is Firefly's."""
    assert effective_due({}, CHILD, TASK, NOV[11]) == NOV[11]


def test_task_ids_normalised_to_str():
    """Integer and string ids refer to the same task."""
    state: dict = {}
    set_change(state, CHILD, 69040, firefly_due=NOV[11], new_due=NOV[18], reason=None, now=NOW)
    observe_firefly_dates(state, CHILD, {"69040": NOV[11]}, NOW)
    assert task_record(state, CHILD, 69040)["active"]["new_due_date"] == "2026-11-18"
    assert effective_due(state, CHILD, 69040, NOV[11]) == NOV[18]


def test_due_date_appearing_or_disappearing_is_a_school_change():
    """Gaining or losing a due date counts as a school change."""
    state = _observed(None)
    observe_firefly_dates(state, CHILD, {TASK: NOV[11]}, NOW)
    observe_firefly_dates(state, CHILD, {TASK: None}, NOW)
    assert task_record(state, CHILD, TASK)["school_changes"] == [
        {"from": None, "to": "2026-11-11", "seen_at": NOW.isoformat()},
        {"from": "2026-11-11", "to": None, "seen_at": NOW.isoformat()},
    ]


@pytest.mark.asyncio
async def test_store_round_trip():
    """The store loads saved changes and class subjects, saves with a delay and can be removed."""
    tasks = {CHILD: {TASK: {"last_firefly_due": "2026-11-11", "active": None, "ended": [], "school_changes": []}}}
    saved = {"tasks": tasks, "class_subjects": {CHILD: {"pabc1 b": "Year 8 Performing Arts"}}}
    store = MagicMock()
    store.async_load = AsyncMock(return_value=saved)
    store.async_remove = AsyncMock()
    with patch("custom_components.firefly_cloud.task_changes.Store", return_value=store) as store_cls:
        changes = TaskChangeStore(MagicMock(), "entry-1")
    assert store_cls.call_args.args[1:] == (1, "firefly_cloud.task_changes.entry-1")

    await changes.async_load()
    assert changes.state == tasks

    changes.async_save_delayed()
    data_func, delay = store.async_delay_save.call_args.args
    assert data_func() == saved
    assert delay == 1

    await changes.async_remove()
    store.async_remove.assert_awaited_once()


@pytest.mark.asyncio
async def test_store_load_empty():
    """With nothing saved yet, the state starts empty."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    with patch("custom_components.firefly_cloud.task_changes.Store", return_value=store):
        changes = TaskChangeStore(MagicMock(), "entry-1")
    await changes.async_load()
    assert changes.state == {}


@pytest.mark.asyncio
async def test_flush_writes_pending_save_now():
    """A pending delayed save is written straight away on flush; nothing is written if nothing is pending."""

    def new_store():
        store = MagicMock()
        store.async_save = AsyncMock()
        with patch("custom_components.firefly_cloud.task_changes.Store", return_value=store):
            return store, TaskChangeStore(MagicMock(), "entry-1")

    store, changes = new_store()
    await changes.async_flush()
    store.async_save.assert_not_awaited()

    store, changes = new_store()
    changes.state["child"] = {}
    changes.async_save_delayed()
    await changes.async_flush()
    store.async_save.assert_awaited_once_with({"tasks": {"child": {}}, "class_subjects": {}})


@pytest.mark.asyncio
async def test_class_subjects_remembered_through_holidays():
    """Class subjects are merged and kept, so an empty timetable (holidays) doesn't lose them."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    with patch("custom_components.firefly_cloud.task_changes.Store", return_value=store):
        changes = TaskChangeStore(MagicMock(), "entry-1")
    await changes.async_load()

    term = {"pabc1 b": "Year 8 Performing Arts"}
    assert changes.remember_class_subjects(CHILD, term) == term
    assert store.async_delay_save.call_count == 1

    # Holidays: no lessons on the timetable
    assert changes.remember_class_subjects(CHILD, {}) == term
    # Nothing new: nothing saved
    assert changes.remember_class_subjects(CHILD, term) == term
    assert store.async_delay_save.call_count == 1

    # A new class, and a code that now means something else
    newer = {"pabc1 b": "Year 9 Drama", "ds9 a": "Year 9 Discovery"}
    assert changes.remember_class_subjects(CHILD, newer) == newer
    assert store.async_delay_save.call_count == 2


def test_moving_to_fireflys_own_date_is_a_note():
    """A "move" to Firefly's own date with a reason is saved as a note, not a move."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[11], reason="Teacher confirmed", now=NOW)
    assert task_record(state, CHILD, TASK)["active"]["new_due_date"] is None
    assert task_record(state, CHILD, TASK)["active"]["reason"] == "Teacher confirmed"


def test_moving_back_to_fireflys_date_without_reason_undoes():
    """Moving a moved task back to Firefly's date with no reason undoes the move (logged)."""
    state = _observed(NOV[11])
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[18], reason=None, now=NOW)
    set_change(state, CHILD, TASK, firefly_due=NOV[11], new_due=NOV[11], reason=None, now=NOW)
    record = task_record(state, CHILD, TASK)
    assert record["active"] is None
    assert record["ended"][-1]["ended_by"] == "undone"


def test_moving_to_fireflys_date_with_nothing_to_undo_is_nothing_to_change():
    """With no change to undo, a move to Firefly's own date and no reason changes nothing."""
    with pytest.raises(ValueError, match="nothing_to_change"):
        set_change(_observed(NOV[11]), CHILD, TASK, firefly_due=NOV[11], new_due=NOV[11], reason=None, now=NOW)


@pytest.mark.asyncio
async def test_saves_after_flush_are_ignored():
    """Once flushed on unload, late save requests (e.g. from an update still running) are ignored."""
    store = MagicMock()
    store.async_load = AsyncMock(return_value=None)
    store.async_save = AsyncMock()
    with patch("custom_components.firefly_cloud.task_changes.Store", return_value=store):
        changes = TaskChangeStore(MagicMock(), "entry-1")
    await changes.async_load()
    await changes.async_flush()

    changes.async_save_delayed()
    changes.remember_class_subjects(CHILD, {"pabc1 b": "Year 8 Performing Arts"})

    store.async_delay_save.assert_not_called()


def test_apply_changes_returns_tasks_with_effective_due():
    """Applying changes gives new tasks carrying the date in force and the change record."""
    with patch("custom_components.firefly_cloud.task_changes.Store"):
        store = TaskChangeStore(MagicMock(), "entry-1")
    observe_firefly_dates(store.state, CHILD, {"t1": NOV[20]}, NOW)
    set_change(store.state, CHILD, "t1", firefly_due=NOV[20], new_due=NOV[25], reason="ill", now=NOW)
    task = make_task("t1", due=NOV[20])

    [applied] = apply_changes(store, CHILD, [task], NOW)

    assert applied.due == date(2026, 11, 25)
    assert applied.firefly_due == date(2026, 11, 20)
    assert applied.due_date_changed is True
    assert applied.change == task_record(store.state, CHILD, "t1")
    assert task.due == NOV[20] and task.change is None


def test_apply_changes_without_store_returns_tasks_unchanged():
    """With no store there is nothing to apply."""
    tasks = [make_task("t1", due=NOV[20])]
    assert apply_changes(None, CHILD, tasks, NOW) is tasks


def test_apply_changes_saves_only_when_firefly_dates_change():
    """The store is saved when Firefly's dates are first seen or change, not otherwise."""
    with patch("custom_components.firefly_cloud.task_changes.Store"):
        store = TaskChangeStore(MagicMock(), "entry-1")
    store.async_save_delayed = MagicMock()
    tasks = [make_task("t1", due=NOV[20])]

    apply_changes(store, CHILD, tasks, NOW)
    apply_changes(store, CHILD, tasks, NOW)

    assert store.async_save_delayed.call_count == 1
    [applied] = apply_changes(store, CHILD, tasks, NOW)
    assert applied.due == NOV[20] and applied.due_date_changed is False
    assert applied.change == task_record(store.state, CHILD, "t1")
