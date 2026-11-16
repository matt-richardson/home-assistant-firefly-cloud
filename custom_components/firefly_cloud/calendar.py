"""Calendar platform for Firefly Cloud integration."""

from datetime import datetime
from typing import List, Optional

from homeassistant.components.calendar import CalendarEntity, CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import dates
from .const import DOMAIN
from .coordinator import FireflyUpdateCoordinator
from .entity import FireflyBaseEntity
from .entry_config import child_guids
from .models import Lesson


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firefly Cloud calendar platform."""
    coordinator: FireflyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create calendar entities for each child
    entities: List[CalendarEntity] = []

    for child_guid in child_guids(config_entry):
        entities.append(
            FireflyCalendar(
                coordinator=coordinator,
                config_entry=config_entry,
                child_guid=child_guid,
            )
        )

    async_add_entities(entities)


class FireflyCalendar(FireflyBaseEntity, CalendarEntity):  # pylint: disable=abstract-method  # read-only
    """Firefly Cloud calendar entity."""

    def __init__(
        self,
        coordinator: FireflyUpdateCoordinator,
        config_entry: ConfigEntry,
        child_guid: str,
    ) -> None:
        """Initialize the calendar."""
        base_name = "Schedule"

        super().__init__(coordinator, config_entry, child_guid, base_name)

        self._config_entry = config_entry

        # Generate unique entity ID
        self._attr_unique_id = f"{config_entry.entry_id}_calendar_{child_guid}"

        # Set entity properties
        self._attr_icon = "mdi:calendar-month"
        self._attr_should_poll = False

    @property
    def event(self) -> Optional[CalendarEvent]:
        """Return the current or next upcoming event."""
        child = self._child
        if child is None or not child.lessons:
            return None

        now = dates.get_offset_time()

        # Find current event
        for lesson in child.lessons:
            if lesson.start <= now <= lesson.end:
                return self._convert_to_calendar_event(lesson)

        # Lessons are sorted by start time, so the first later one is next
        for lesson in child.lessons:
            if lesson.start > now:
                return self._convert_to_calendar_event(lesson)

        return None

    async def async_get_events(
        self,
        hass: HomeAssistant,  # pylint: disable=unused-argument
        start_date: datetime,
        end_date: datetime,
    ) -> List[CalendarEvent]:
        """Return calendar events within a datetime range."""
        child = self._child
        if child is None:
            return []

        # Events that overlap the requested range
        return [
            self._convert_to_calendar_event(lesson)
            for lesson in child.lessons
            if lesson.end >= start_date and lesson.start <= end_date
        ]

    def _convert_to_calendar_event(self, lesson: Lesson) -> CalendarEvent:
        """Convert a lesson to a CalendarEvent."""
        return CalendarEvent(
            start=lesson.start,
            end=lesson.end,
            summary=lesson.subject,  # type: ignore[arg-type]  # Firefly may send null
            description=self._build_event_description(lesson),
            location=lesson.location,
        )

    def _build_event_description(self, lesson: Lesson) -> Optional[str]:
        """Build a comprehensive event description."""
        description_parts = []

        if lesson.description:
            description_parts.append(lesson.description)

        if lesson.guild:
            description_parts.append(f"Class: {lesson.guild}")

        if lesson.attendees:
            attendees = lesson.attendees[:5]  # Limit to first 5
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
            if len(lesson.attendees) > 5:
                attendees_str += f" and {len(lesson.attendees) - 5} more"
            description_parts.append(f"Attendees: {attendees_str}")

        return "\n".join(description_parts) if description_parts else None
