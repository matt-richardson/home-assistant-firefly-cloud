"""Calendar platform for Firefly Cloud integration."""

from datetime import datetime
from typing import List, Optional

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHILDREN_GUIDS,
    CONF_SCHOOL_NAME,
    CONF_USER_GUID,
    DOMAIN,
)
from .coordinator import FireflyUpdateCoordinator



async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firefly Cloud calendar platform."""
    coordinator: FireflyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Get children GUIDs from config or use user GUID if no children
    children_guids = config_entry.data.get(CONF_CHILDREN_GUIDS, [])
    if not children_guids:
        children_guids = [config_entry.data[CONF_USER_GUID]]

    # Create calendar entities for each child
    entities: List[CalendarEntity] = []

    for child_guid in children_guids:
        entities.append(
            FireflyCalendar(
                coordinator=coordinator,
                config_entry=config_entry,
                child_guid=child_guid,
            )
        )

    async_add_entities(entities)


class FireflyCalendar(CalendarEntity):
    """Firefly Cloud calendar entity."""

    def __init__(
        self,
        coordinator: FireflyUpdateCoordinator,
        config_entry: ConfigEntry,
        child_guid: str,
    ) -> None:
        """Initialize the calendar."""
        super().__init__()
        self.coordinator = coordinator
        self._config_entry = config_entry
        self._child_guid = child_guid
        self._unsub_coordinator = None

        # Generate unique entity ID
        school_name = config_entry.data.get(CONF_SCHOOL_NAME, "firefly")
        self._attr_unique_id = f"{config_entry.entry_id}_calendar_{child_guid}"

        # Set entity properties - will be updated with child name when data is available
        self._base_name = f"{school_name} Schedule"
        self._attr_name = f"{self._base_name} ({child_guid[:8]})"
        self._attr_icon = "mdi:calendar-month"
        self._attr_should_poll = False
        self._attr_available = False  # Will be updated by coordinator

        # Device info for grouping
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"Firefly Cloud - {school_name}",
            manufacturer="Firefly Learning",
            model="Firefly Cloud Integration",
            sw_version="1.0.0",
            configuration_url=config_entry.data.get("host"),
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Subscribe to coordinator updates
        self._unsub_coordinator = self.coordinator.async_add_listener(self._handle_coordinator_update)  # type: ignore

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        if self._unsub_coordinator:
            self._unsub_coordinator()
        await super().async_will_remove_from_hass()

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._child_guid in self.coordinator.data.get("children_data", {})
        )

    @property
    def name(self) -> str:
        """Return the display name of the calendar."""
        if self.coordinator.data and self._child_guid in self.coordinator.data.get("children_data", {}):
            child_data = self.coordinator.data["children_data"][self._child_guid]
            child_name = child_data.get("name")
            if child_name:
                return f"{self._base_name} ({child_name})"
        return self._attr_name or f"{self._base_name} ({self._child_guid[:8]})"

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def event(self) -> Optional[CalendarEvent]:
        """Return the current or next upcoming event."""
        if not self.coordinator.data:
            return None

        # Check if child data exists
        if self._child_guid not in self.coordinator.data.get("children_data", {}):
            return None

        # Get events for this child
        child_data = self.coordinator.data["children_data"][self._child_guid]
        events = child_data.get("events", {}).get("week", [])

        if not events:
            return None

        now = dt_util.now()

        # Find current event
        for event in events:
            if event["start"] <= now <= event["end"]:
                return self._convert_to_calendar_event(event)

        # Find next upcoming event
        upcoming_events = [e for e in events if e["start"] > now]
        if upcoming_events:
            # Events are already sorted by start time in coordinator
            return self._convert_to_calendar_event(upcoming_events[0])

        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,  # pylint: disable=unused-argument
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Return calendar events within a datetime range."""
        if not self.coordinator.data:
            return []

        # Check if child data exists
        if self._child_guid not in self.coordinator.data.get("children_data", {}):
            return []

        # Get events for this child
        child_data = self.coordinator.data["children_data"][self._child_guid]
        events = child_data.get("events", {}).get("week", [])

        # Filter events within the requested date range
        calendar_events = []
        for event in events:
            event_start = event["start"]
            event_end = event["end"]

            # Check if event overlaps with requested range
            if event_end >= start_date and event_start <= end_date:
                calendar_events.append(self._convert_to_calendar_event(event))

        return calendar_events

    def _convert_to_calendar_event(self, event: dict) -> CalendarEvent:
        """Convert Firefly event to CalendarEvent."""
        return CalendarEvent(
            start=event["start"],
            end=event["end"],
            summary=event["subject"],
            description=self._build_event_description(event),
            location=event.get("location"),
        )

    def _build_event_description(self, event: dict) -> Optional[str]:
        """Build a comprehensive event description."""
        description_parts = []

        if event.get("description"):
            description_parts.append(event["description"])

        if event.get("guild"):
            description_parts.append(f"Class: {event['guild']}")

        if event.get("attendees"):
            attendees = event["attendees"][:5]  # Limit to first 5
            # Handle both string and dict attendees
            attendee_names = []
            for attendee in attendees:
                if isinstance(attendee, dict):
                    # Extract name from dict
                    attendee_names.append(attendee.get("name", "Unknown"))
                else:
                    # Already a string
                    attendee_names.append(str(attendee))

            attendees_str = ", ".join(attendee_names)
            if len(event["attendees"]) > 5:
                attendees_str += f" and {len(event['attendees']) - 5} more"
            description_parts.append(f"Attendees: {attendees_str}")

        return "\n".join(description_parts) if description_parts else None

    async def async_create_event(self, **kwargs) -> None:  # pylint: disable=unused-argument
        """Create a new event."""
        raise NotImplementedError("Firefly Cloud integration is read-only")

    async def async_delete_event(
        self,
        uid: str,  # pylint: disable=unused-argument
        recurrence_id: str | None = None,  # pylint: disable=unused-argument
        recurrence_range: str | None = None,  # pylint: disable=unused-argument
    ) -> None:
        """Delete an event."""
        raise NotImplementedError("Firefly Cloud integration is read-only")

    async def async_update_event(
        self,
        uid: str,  # pylint: disable=unused-argument
        event: dict,  # pylint: disable=unused-argument
        recurrence_id: str | None = None,  # pylint: disable=unused-argument
        recurrence_range: str | None = None,  # pylint: disable=unused-argument
    ) -> None:
        """Update an event."""
        raise NotImplementedError("Firefly Cloud integration is read-only")
