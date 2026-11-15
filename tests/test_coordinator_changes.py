"""Tests for applying dashboard due date changes in the coordinator."""

from datetime import datetime, timedelta

import pytest
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import UpdateFailed

from custom_components.firefly_cloud.coordinator import FireflyUpdateCoordinator
from custom_components.firefly_cloud.exceptions import FireflyConnectionError
from tests.conftest import firefly_due


@pytest.fixture
def change_store():
    """A TaskChangeStore whose persistence is mocked."""
    from unittest.mock import MagicMock, patch

    from custom_components.firefly_cloud.task_changes import TaskChangeStore

    with patch("custom_components.firefly_cloud.task_changes.Store"):
        store = TaskChangeStore(MagicMock(), "entry-1")
    return store


def _dated_task(task_id, days_from_today, title=None):
    return {
        "id": task_id,
        "title": title or f"task {task_id}",
        "dueDate": firefly_due(days_from_today),
        "completionStatus": "Todo",
    }


def _child(data):
    return next(iter(data["children_data"].values()))


def _titles(tasks):
    return [t["title"] for t in tasks]


async def _coordinator_with(hass, mock_api, change_store, tasks):
    mock_api.get_tasks.return_value = tasks
    coordinator = FireflyUpdateCoordinator(hass=hass, api=mock_api, task_lookahead_days=7, change_store=change_store)
    coordinator.data = await coordinator._async_update_data()
    return coordinator


def _today():
    from custom_components.firefly_cloud.const import get_offset_time

    return get_offset_time().date()


@pytest.mark.asyncio
async def test_change_moves_task_out_of_overdue(hass: HomeAssistant, mock_api, change_store):
    """A dashboard date change counts straight away in the filters."""
    from custom_components.firefly_cloud.task_changes import set_change

    coordinator = await _coordinator_with(hass, mock_api, change_store, [_dated_task(1, -1, "Late")])
    child_guid = next(iter(coordinator.data["children_data"]))
    set_change(
        change_store.state,
        child_guid,
        1,
        firefly_due=_today() - timedelta(days=1),
        new_due=_today() + timedelta(days=3),
        reason="x",
        now=datetime.now(),
    )

    tasks = _child(await coordinator._async_update_data())["tasks"]

    assert _titles(tasks["overdue"]) == []
    assert _titles(tasks["upcoming"]) == ["Late"]
    [task] = tasks["upcoming"]
    assert task["due_date_changed"] is True
    assert task["due_date_change_reason"] == "x"
    assert task["firefly_due_date"] == _today() - timedelta(days=1)
    assert task["due_date"].date() == _today() + timedelta(days=3)
    assert task["change"]["active"]["new_due_date"] == (_today() + timedelta(days=3)).isoformat()


@pytest.mark.asyncio
async def test_unchanged_task_fields(hass: HomeAssistant, mock_api, change_store):
    """Tasks without a change report Firefly's date and no change."""
    coordinator = await _coordinator_with(hass, mock_api, change_store, [_dated_task(1, 2)])
    [task] = _child(coordinator.data)["tasks"]["all"]
    assert task["due_date_changed"] is False
    assert task["due_date_change_reason"] is None
    assert task["firefly_due_date"] == _today() + timedelta(days=2)
    assert task["change"]["active"] is None


@pytest.mark.asyncio
async def test_note_only_stays_overdue(hass: HomeAssistant, mock_api, change_store):
    """A note doesn't change the date, so the task stays overdue."""
    from custom_components.firefly_cloud.task_changes import set_change

    coordinator = await _coordinator_with(hass, mock_api, change_store, [_dated_task(1, -1, "Late")])
    child_guid = next(iter(coordinator.data["children_data"]))
    set_change(
        change_store.state,
        child_guid,
        1,
        firefly_due=_today() - timedelta(days=1),
        new_due=None,
        reason="Doing it in class today",
        now=datetime.now(),
    )

    tasks = _child(await coordinator._async_update_data())["tasks"]

    assert _titles(tasks["overdue"]) == ["Late"]
    assert tasks["overdue"][0]["due_date_changed"] is False
    assert tasks["overdue"][0]["due_date_change_reason"] == "Doing it in class today"


@pytest.mark.asyncio
async def test_school_change_wins(hass: HomeAssistant, mock_api, change_store):
    """When Firefly's date changes, it replaces the dashboard date."""
    from custom_components.firefly_cloud.task_changes import set_change

    coordinator = await _coordinator_with(hass, mock_api, change_store, [_dated_task(1, 0)])
    child_guid = next(iter(coordinator.data["children_data"]))
    set_change(
        change_store.state,
        child_guid,
        1,
        firefly_due=_today(),
        new_due=_today() + timedelta(days=5),
        reason=None,
        now=datetime.now(),
    )

    mock_api.get_tasks.return_value = [_dated_task(1, 2)]
    [task] = _child(await coordinator._async_update_data())["tasks"]["all"]

    assert task["due_date"].date() == _today() + timedelta(days=2)
    assert task["due_date_changed"] is False
    assert task["change"]["ended"][-1]["ended_by"] == "school_changed"


@pytest.mark.asyncio
async def test_observing_saves_store(hass: HomeAssistant, mock_api, change_store):
    """New or changed Firefly dates are saved; an unchanged poll doesn't save again."""
    from unittest.mock import MagicMock

    change_store.async_save_delayed = MagicMock()
    coordinator = await _coordinator_with(hass, mock_api, change_store, [_dated_task(1, 2)])
    saves = change_store.async_save_delayed.call_count
    assert saves >= 1
    await coordinator._async_update_data()
    assert change_store.async_save_delayed.call_count == saves


@pytest.mark.asyncio
async def test_rebuild_does_not_call_api(hass: HomeAssistant, mock_api, change_store):
    """Rebuilding after a change reuses the last fetch and pushes the new data."""
    from unittest.mock import MagicMock

    from custom_components.firefly_cloud.task_changes import set_change

    coordinator = await _coordinator_with(hass, mock_api, change_store, [_dated_task(1, -1, "Late")])
    coordinator.async_set_updated_data = MagicMock()
    coordinator.async_update_listeners = MagicMock()
    change_store.async_save_delayed = MagicMock()
    calls = (mock_api.get_tasks.call_count, mock_api.get_events.call_count)
    child_guid = next(iter(coordinator.data["children_data"]))
    set_change(
        change_store.state,
        child_guid,
        1,
        firefly_due=_today() - timedelta(days=1),
        new_due=_today(),
        reason=None,
        now=datetime.now(),
    )

    await coordinator.async_rebuild_from_last_fetch()

    assert (mock_api.get_tasks.call_count, mock_api.get_events.call_count) == calls
    # Entities are updated without rescheduling the next Firefly poll
    coordinator.async_set_updated_data.assert_not_called()
    coordinator.async_update_listeners.assert_called_once()
    assert coordinator.last_update_success is True
    new_data = coordinator.data
    assert _titles(_child(new_data)["tasks"]["due_today"]) == ["Late"]
    assert _child(new_data)["events"] == _child(coordinator.data)["events"]
    # The service saves the change itself; with no new Firefly dates the rebuild has nothing to save
    change_store.async_save_delayed.assert_not_called()


@pytest.mark.asyncio
async def test_rebuild_without_data_does_nothing(hass: HomeAssistant, mock_api, change_store):
    """Before the first successful update there's nothing to rebuild."""
    from unittest.mock import MagicMock

    coordinator = FireflyUpdateCoordinator(hass=hass, api=mock_api, change_store=change_store)
    coordinator.async_set_updated_data = MagicMock()
    await coordinator.async_rebuild_from_last_fetch()
    coordinator.async_set_updated_data.assert_not_called()


@pytest.mark.asyncio
async def test_failed_update_keeps_changes(hass: HomeAssistant, mock_api, change_store):
    """A failed fetch never clears saved changes."""
    from custom_components.firefly_cloud.task_changes import set_change, task_record

    coordinator = await _coordinator_with(hass, mock_api, change_store, [_dated_task(1, -1)])
    child_guid = next(iter(coordinator.data["children_data"]))
    set_change(
        change_store.state,
        child_guid,
        1,
        firefly_due=_today() - timedelta(days=1),
        new_due=_today(),
        reason=None,
        now=datetime.now(),
    )

    mock_api.get_tasks.side_effect = FireflyConnectionError("down")
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert task_record(change_store.state, child_guid, 1)["active"] is not None


@pytest.mark.asyncio
async def test_partial_failure_leaves_store_and_last_fetch_untouched(hass: HomeAssistant, mock_api, change_store):
    """If any child's fetch fails, no child's dates are observed and the last fetch is kept as it was."""
    from custom_components.firefly_cloud.task_changes import set_change, task_record

    mock_api.get_tasks.side_effect = None
    mock_api.get_tasks.return_value = [_dated_task(1, 0)]
    coordinator = FireflyUpdateCoordinator(
        hass=hass, api=mock_api, task_lookahead_days=7, change_store=change_store, children_guids=["a", "b"]
    )
    coordinator.data = await coordinator._async_update_data()
    set_change(
        change_store.state,
        "a",
        1,
        firefly_due=_today(),
        new_due=_today() + timedelta(days=5),
        reason=None,
        now=datetime.now(),
    )
    last_raw = {guid: dict(raw) for guid, raw in coordinator._last_raw.items()}

    async def tasks_for(student_guid):
        if student_guid == "b":
            raise FireflyConnectionError("down")
        return [_dated_task(1, 2)]  # the school moved child a's task

    mock_api.get_tasks.side_effect = tasks_for
    with pytest.raises(UpdateFailed):
        await coordinator._async_update_data()

    assert task_record(change_store.state, "a", 1)["active"] is not None
    assert task_record(change_store.state, "a", 1)["school_changes"] == []
    assert coordinator._last_raw == last_raw


@pytest.mark.asyncio
async def test_rebuild_during_outage_keeps_entities_unavailable(hass: HomeAssistant, mock_api, change_store):
    """A change saved while Firefly is down is applied, but doesn't mark the stale data as a successful update."""
    from unittest.mock import MagicMock

    from custom_components.firefly_cloud.task_changes import set_change

    coordinator = await _coordinator_with(hass, mock_api, change_store, [_dated_task(1, -1, "Late")])
    coordinator.last_update_success = False  # the last poll failed
    coordinator.async_set_updated_data = MagicMock()
    coordinator.async_update_listeners = MagicMock()
    child_guid = next(iter(coordinator.data["children_data"]))
    set_change(
        change_store.state,
        child_guid,
        1,
        firefly_due=_today() - timedelta(days=1),
        new_due=_today(),
        reason=None,
        now=datetime.now(),
    )

    await coordinator.async_rebuild_from_last_fetch()

    coordinator.async_set_updated_data.assert_not_called()
    coordinator.async_update_listeners.assert_called_once()
    assert coordinator.last_update_success is False
    assert _titles(_child(coordinator.data)["tasks"]["due_today"]) == ["Late"]


@pytest.mark.asyncio
async def test_subjects_survive_holidays(hass: HomeAssistant, mock_api, change_store):
    """Class subjects seen during term are remembered, so tasks keep their subject when the timetable is empty."""
    task = {"id": 1, "title": "A", "dueDate": firefly_due(2), "addressees": [{"name": "Class PABC1 B"}]}
    mock_api.get_tasks.return_value = [task]
    mock_api.get_events.return_value = [
        {
            "start": "2026-11-16T21:55:00Z",
            "end": "2026-11-16T22:55:00Z",
            "subject": "Year 8 Performing Arts",
            "description": "PABC1 B\nAttendees: Unknown",
        }
    ]
    coordinator = await _coordinator_with(hass, mock_api, change_store, [task])

    mock_api.get_events.return_value = []  # holidays
    [processed] = _child(await coordinator._async_update_data())["tasks"]["all"]

    assert processed["subject"] == "Year 8 Performing Arts"
