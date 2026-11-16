"""Services for changing a task's due date (or adding a note) from Home Assistant.

Firefly's own due date can't be changed from here; the change is kept in Home
Assistant (see task_changes.py) and applied on top of Firefly's date.
"""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.util import dt as dt_util

from .child_lookup import resolve_child
from .const import DOMAIN
from .coordinator import FireflyUpdateCoordinator
from .models import Task
from .task_changes import TaskChangeStore, clear_change, set_change

SERVICE_SET_TASK_DUE_DATE = "set_task_due_date"
SERVICE_CLEAR_TASK_DUE_DATE = "clear_task_due_date"

ATTR_TASK_ID = "task_id"
ATTR_DUE_DATE = "due_date"
ATTR_REASON = "reason"
MAX_REASON_LENGTH = 200


# Schemas use voluptuous so older Home Assistant keeps working; newer HA's type hints expect probatio
def _single_entity(entity_ids: list[str]) -> str:
    """Accept entity_id as one entity or a one-item list (as automations' target: sends it)."""
    if len(entity_ids) != 1:
        raise vol.Invalid("Target exactly one Firefly tasks list")
    return entity_ids[0]


_BASE_SCHEMA: dict[Any, Any] = {
    vol.Required("entity_id"): vol.All(cv.entity_ids, _single_entity),
    vol.Required(ATTR_TASK_ID): cv.string,
}
SET_SCHEMA = vol.Schema(
    {
        **_BASE_SCHEMA,
        vol.Optional(ATTR_DUE_DATE): cv.date,
        vol.Optional(ATTR_REASON): vol.All(cv.string, vol.Length(max=MAX_REASON_LENGTH)),
    }
)
CLEAR_SCHEMA = vol.Schema(_BASE_SCHEMA)


def _error(key: str, **placeholders: str) -> ServiceValidationError:
    return ServiceValidationError(translation_domain=DOMAIN, translation_key=key, translation_placeholders=placeholders)


def _resolve_task(
    hass: HomeAssistant, call: ServiceCall
) -> tuple[FireflyUpdateCoordinator, TaskChangeStore, str, Task]:
    """Find the coordinator, its change store, and the child and open task a service call targets."""
    entity_id = call.data["entity_id"]
    resolved = resolve_child(hass, entity_id)
    if resolved is None:
        raise _error("entity_not_found", entity_id=entity_id)
    coordinator, child_guid = resolved
    store = coordinator.change_store
    assert store is not None  # resolve_child only returns coordinators with a change store
    task_id = call.data[ATTR_TASK_ID]
    child = coordinator.data.child(child_guid) if coordinator.data is not None else None
    task = next((t for t in child.tasks if t.id == task_id), None) if child is not None else None
    if task is None:
        raise _error("task_not_found", task_id=task_id)
    return coordinator, store, child_guid, task


async def _async_set_task_due_date(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator, store, child_guid, task = _resolve_task(hass, call)
    try:
        set_change(
            store.state,
            child_guid,
            task.id,
            firefly_due=task.firefly_due,
            new_due=call.data.get(ATTR_DUE_DATE),
            reason=call.data.get(ATTR_REASON),
            now=dt_util.now(),
        )
    except ValueError as err:
        raise _error(str(err)) from err
    store.async_save_delayed()
    await coordinator.async_rebuild_from_last_fetch()


async def _async_clear_task_due_date(hass: HomeAssistant, call: ServiceCall) -> None:
    coordinator, store, child_guid, task = _resolve_task(hass, call)
    try:
        clear_change(store.state, child_guid, task.id, dt_util.now())
    except ValueError as err:
        raise _error(str(err)) from err
    store.async_save_delayed()
    await coordinator.async_rebuild_from_last_fetch()


def async_setup_services(hass: HomeAssistant) -> None:
    """Register the services (once per Home Assistant instance)."""
    if hass.services.has_service(DOMAIN, SERVICE_SET_TASK_DUE_DATE):
        return

    async def set_due(call: ServiceCall) -> None:
        await _async_set_task_due_date(hass, call)

    async def clear_due(call: ServiceCall) -> None:
        await _async_clear_task_due_date(hass, call)

    set_schema: Any = SET_SCHEMA
    clear_schema: Any = CLEAR_SCHEMA
    hass.services.async_register(DOMAIN, SERVICE_SET_TASK_DUE_DATE, set_due, schema=set_schema)
    hass.services.async_register(DOMAIN, SERVICE_CLEAR_TASK_DUE_DATE, clear_due, schema=clear_schema)


def async_unload_services(hass: HomeAssistant) -> None:
    """Remove the services (when the last config entry unloads)."""
    hass.services.async_remove(DOMAIN, SERVICE_SET_TASK_DUE_DATE)
    hass.services.async_remove(DOMAIN, SERVICE_CLEAR_TASK_DUE_DATE)
