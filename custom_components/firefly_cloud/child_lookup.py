"""Find which child a Firefly tasks list (todo entity) belongs to.

Used by the services and the cards' websocket command, which are both given the
child's todo entity.
"""

from __future__ import annotations

from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

# Firefly todo entities have unique ids "<config entry id>_todo_<child guid>"
TODO_UNIQUE_ID_MARKER = "_todo_"


def firefly_todo_child(hass: HomeAssistant, entity_id: str) -> tuple[str, str] | None:
    """Return (config_entry_id, child_guid) if this is a Firefly tasks list, loaded or not."""
    entry = er.async_get(hass).async_get(entity_id)
    if entry is None or entry.platform != DOMAIN or entry.domain != "todo" or entry.config_entry_id is None:
        return None
    unique_id = entry.unique_id or ""
    if TODO_UNIQUE_ID_MARKER not in unique_id:
        return None
    return entry.config_entry_id, unique_id.split(TODO_UNIQUE_ID_MARKER, 1)[1]


def resolve_child(hass: HomeAssistant, entity_id: str) -> tuple[Any, str] | None:
    """Return (coordinator, child_guid) for a loaded Firefly tasks list, or None."""
    found = firefly_todo_child(hass, entity_id)
    if found is None:
        return None
    entry_id, child_guid = found
    coordinator = hass.data.get(DOMAIN, {}).get(entry_id)
    if coordinator is None or getattr(coordinator, "change_store", None) is None:
        return None
    return coordinator, child_guid
