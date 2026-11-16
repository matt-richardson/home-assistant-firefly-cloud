"""Tests for the task due date services."""

from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from conftest import make_child, make_data, make_task
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError

from custom_components.firefly_cloud.const import DOMAIN
from custom_components.firefly_cloud.services import (
    SERVICE_CLEAR_TASK_DUE_DATE,
    SERVICE_SET_TASK_DUE_DATE,
    async_setup_services,
    async_unload_services,
)
from custom_components.firefly_cloud.task_changes import TaskChangeStore, task_record

ENTITY = "todo.example_school_tasks_alex"
CHILD = "child-guid-1"
ENTRY = "entry-1"


@pytest.fixture
def coordinator():
    """A coordinator with one child, one task in the lookahead window and one beyond it."""
    with patch("custom_components.firefly_cloud.task_changes.Store"):
        store = TaskChangeStore(MagicMock(), ENTRY)
    coord = MagicMock()
    coord.change_store = store
    coord.async_rebuild_from_last_fetch = AsyncMock()
    coord.data = make_data(
        make_child(
            CHILD,
            tasks=[
                make_task("69040", title="Model Car", due=date(2026, 11, 11)),
                make_task("70000", title="Far away", due=date(2026, 12, 20)),
            ],
            today=date(2026, 11, 10),
        )
    )
    return coord


@pytest.fixture
def registry():
    """An entity registry knowing one Firefly todo entity and one unrelated sensor."""
    entries = {
        ENTITY: MagicMock(platform=DOMAIN, domain="todo", config_entry_id=ENTRY, unique_id=f"{ENTRY}_todo_{CHILD}"),
        "sensor.other": MagicMock(platform="other", domain="sensor", config_entry_id="x", unique_id="y"),
        "todo.weird": MagicMock(platform=DOMAIN, domain="todo", config_entry_id=ENTRY, unique_id="no-marker"),
    }
    reg = MagicMock()
    reg.async_get.side_effect = entries.get
    with patch("custom_components.firefly_cloud.child_lookup.er.async_get", return_value=reg):
        yield reg


@pytest_asyncio.fixture
async def services(hass: HomeAssistant, coordinator, registry):
    """Services registered, with the coordinator in hass.data."""
    hass.data.setdefault(DOMAIN, {})[ENTRY] = coordinator
    async_setup_services(hass)
    yield
    hass.data.pop(DOMAIN, None)


async def _call(hass, service, **data):
    await hass.services.async_call(DOMAIN, service, {"entity_id": ENTITY, **data}, blocking=True)


def _record(coordinator, task_id="69040"):
    return task_record(coordinator.change_store.state, CHILD, task_id)


@pytest.mark.asyncio
async def test_set_due_date_updates_coordinator(hass, services, coordinator):
    """Setting a date saves the change with Firefly's date, then rebuilds without calling Firefly."""
    await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="69040", due_date="2026-11-18", reason="Extended in class")
    active = _record(coordinator)["active"]
    assert active["new_due_date"] == "2026-11-18"
    assert active["reason"] == "Extended in class"
    assert active["firefly_due_at_change"] == "2026-11-11"
    coordinator.async_rebuild_from_last_fetch.assert_awaited_once()


@pytest.mark.asyncio
async def test_set_note_only(hass, services, coordinator):
    """A reason without a date saves a note."""
    await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="69040", reason="Doing it in class today")
    assert _record(coordinator)["active"]["new_due_date"] is None


@pytest.mark.asyncio
async def test_set_requires_date_or_reason(hass, services, coordinator):
    """With neither a date nor a reason there's nothing to save."""
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="69040", reason="  ")
    assert err.value.translation_key == "nothing_to_change"
    coordinator.async_rebuild_from_last_fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_clear_logs_undo(hass, services, coordinator):
    """Undo ends the change and keeps it in the history."""
    await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="69040", due_date="2026-11-18")
    await _call(hass, SERVICE_CLEAR_TASK_DUE_DATE, task_id="69040")
    record = _record(coordinator)
    assert record["active"] is None
    assert record["ended"][-1]["ended_by"] == "undone"
    assert coordinator.async_rebuild_from_last_fetch.await_count == 2


@pytest.mark.asyncio
async def test_clear_without_change(hass, services):
    """Undo with nothing to undo is a validation error."""
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, SERVICE_CLEAR_TASK_DUE_DATE, task_id="69040")
    assert err.value.translation_key == "no_change"


@pytest.mark.asyncio
@pytest.mark.parametrize("entity_id", ["todo.missing", "sensor.other", "todo.weird"])
async def test_unknown_entity(hass, services, entity_id):
    """Only Firefly todo entities are accepted."""
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(
            DOMAIN, SERVICE_SET_TASK_DUE_DATE, {"entity_id": entity_id, "task_id": "1", "reason": "x"}, blocking=True
        )
    assert err.value.translation_key == "entity_not_found"


@pytest.mark.asyncio
async def test_entry_not_loaded(hass, services):
    """A Firefly todo entity whose config entry isn't loaded is not found."""
    hass.data[DOMAIN].pop(ENTRY)
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="69040", reason="x")
    assert err.value.translation_key == "entity_not_found"


@pytest.mark.asyncio
async def test_unknown_task(hass, services):
    """A task id that isn't one of the child's open tasks is rejected."""
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="1", reason="x")
    assert err.value.translation_key == "task_not_found"


@pytest.mark.asyncio
async def test_task_not_found_before_first_refresh(hass, services, coordinator):
    """Before the coordinator has data, any task id is reported as not found."""
    coordinator.data = None
    with pytest.raises(ServiceValidationError) as err:
        await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="69040", reason="x")
    assert err.value.translation_key == "task_not_found"


@pytest.mark.asyncio
async def test_task_beyond_lookahead_can_be_changed(hass, services, coordinator):
    """Tasks outside the upcoming window (only in 'all') can still be changed."""
    await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="70000", due_date="2026-12-24")
    assert _record(coordinator, "70000")["active"]["new_due_date"] == "2026-12-24"


@pytest.mark.asyncio
async def test_setup_is_idempotent_and_unloads(hass, services):
    """Registering twice is harmless; unloading removes both services."""
    async_setup_services(hass)
    assert hass.services.has_service(DOMAIN, SERVICE_SET_TASK_DUE_DATE)
    async_unload_services(hass)
    assert not hass.services.has_service(DOMAIN, SERVICE_SET_TASK_DUE_DATE)
    assert not hass.services.has_service(DOMAIN, SERVICE_CLEAR_TASK_DUE_DATE)


@pytest.mark.asyncio
async def test_change_is_saved_before_rebuild(hass, services, coordinator):
    """A successful change is saved by the service itself, whatever the rebuild does."""
    coordinator.change_store.async_save_delayed = MagicMock()
    await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="69040", reason="x")
    coordinator.change_store.async_save_delayed.assert_called_once()
    await _call(hass, SERVICE_CLEAR_TASK_DUE_DATE, task_id="69040")
    assert coordinator.change_store.async_save_delayed.call_count == 2


@pytest.mark.asyncio
async def test_rejected_change_is_not_saved(hass, services, coordinator):
    """Nothing is saved when a request is rejected."""
    coordinator.change_store.async_save_delayed = MagicMock()
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_SET_TASK_DUE_DATE, task_id="69040")
    with pytest.raises(ServiceValidationError):
        await _call(hass, SERVICE_CLEAR_TASK_DUE_DATE, task_id="69040")
    coordinator.change_store.async_save_delayed.assert_not_called()


@pytest.mark.asyncio
async def test_target_style_entity_list_accepted(hass, services, coordinator):
    """Automations using target: pass entity_id as a list; one entity is accepted."""
    await hass.services.async_call(
        DOMAIN, SERVICE_SET_TASK_DUE_DATE, {"entity_id": [ENTITY], "task_id": "69040", "reason": "x"}, blocking=True
    )
    assert _record(coordinator)["active"]["reason"] == "x"


@pytest.mark.asyncio
async def test_more_than_one_entity_rejected(hass, services):
    """A task belongs to one child, so exactly one tasks list must be targeted."""
    import voluptuous as vol

    with pytest.raises(vol.Invalid):
        await hass.services.async_call(
            DOMAIN,
            SERVICE_CLEAR_TASK_DUE_DATE,
            {"entity_id": [ENTITY, "todo.other"], "task_id": "69040"},
            blocking=True,
        )
