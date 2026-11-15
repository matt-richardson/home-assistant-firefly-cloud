"""Sensor platform for Firefly Cloud integration."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from . import dates
from .const import (
    CONF_SHOW_CLASS_TIMES,
    DEFAULT_SHOW_CLASS_TIMES,
    DOMAIN,
    SENSOR_CURRENT_CLASS,
    SENSOR_NEXT_CLASS,
    SENSOR_OVERDUE_TASKS,
    SENSOR_TASKS_DUE_TODAY,
    SENSOR_TYPES,
    SENSOR_UPCOMING_TASKS,
)
from .coordinator import FireflyUpdateCoordinator
from .entity import FireflyBaseEntity
from .entry_config import child_guids, entry_option
from .models import UNKNOWN_SUBJECT, ChildData, Lesson, Task


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firefly Cloud sensor platform."""
    coordinator: FireflyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create sensors for each child and each sensor type
    entities: List[SensorEntity] = []

    for child_guid in child_guids(config_entry):
        for sensor_type in SENSOR_TYPES:
            entities.append(
                FireflySensor(
                    coordinator=coordinator,
                    config_entry=config_entry,
                    sensor_type=sensor_type,
                    child_guid=child_guid,
                )
            )

    async_add_entities(entities)


def _change_attributes(task: Task) -> Dict[str, Any]:
    """Return a task's dashboard due date change fields for entity attributes (no history)."""
    return {
        "firefly_due_date": task.firefly_due.isoformat() if task.firefly_due else None,
        "due_date_changed": task.due_date_changed,
        "due_date_change_reason": task.change_reason,
    }


def _description(task: Task) -> str | None:
    """Return a task's description, cut to 100 characters."""
    if task.description and len(task.description) > 100:
        return task.description[:100] + "..."
    return task.description


class FireflySensor(FireflyBaseEntity, SensorEntity):
    """Base Firefly sensor."""

    def __init__(
        self,
        coordinator: FireflyUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_type: str,
        child_guid: str,
    ) -> None:
        """Initialize the sensor."""
        sensor_config = SENSOR_TYPES[sensor_type]
        base_name = sensor_config["name"]

        super().__init__(coordinator, config_entry, child_guid, base_name)

        self._config_entry = config_entry
        self._sensor_type = sensor_type
        self._sensor_config = sensor_config

        # Generate unique entity ID
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}_{child_guid}"

        # Set entity properties
        self._attr_icon = sensor_config["icon"]
        self._attr_native_unit_of_measurement = sensor_config["unit"]

        # Only set device_class if it's not None and cast to proper type
        device_class = sensor_config.get("device_class")
        if device_class is not None:
            if isinstance(device_class, str):
                try:
                    self._attr_device_class = SensorDeviceClass(device_class)
                except ValueError:
                    pass
            else:
                self._attr_device_class = device_class

    @property
    def native_value(self) -> Optional[str | int]:
        """Return the state of the sensor."""
        child = self._child
        if child is None:
            return None

        return self._calculate_sensor_value(child)

    def _calculate_sensor_value(self, child: ChildData) -> Optional[str | int]:
        """Calculate the sensor value based on sensor type."""
        if self._sensor_type == SENSOR_UPCOMING_TASKS:
            return len(child.upcoming)
        if self._sensor_type == SENSOR_TASKS_DUE_TODAY:
            return len(child.due_today)
        if self._sensor_type == SENSOR_OVERDUE_TASKS:
            return len(child.overdue)
        if self._sensor_type == SENSOR_CURRENT_CLASS:
            return self._get_current_class(child)
        if self._sensor_type == SENSOR_NEXT_CLASS:
            return self._get_next_class(child)
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        child = self._child
        if child is None:
            # Unavailable, so Home Assistant doesn't show attributes
            return {}

        attributes = {
            "last_updated": self.coordinator.data.last_updated,
            "child_guid": self._child_guid,
        }

        if self._sensor_type == SENSOR_UPCOMING_TASKS:
            attributes.update(self._get_upcoming_tasks_attributes(child))
        elif self._sensor_type == SENSOR_TASKS_DUE_TODAY:
            attributes.update(self._get_tasks_due_today_attributes(child))
        elif self._sensor_type == SENSOR_OVERDUE_TASKS:
            attributes.update(self._get_overdue_tasks_attributes(child))
        elif self._sensor_type == SENSOR_CURRENT_CLASS:
            attributes.update(self._get_current_class_attributes(child))
        elif self._sensor_type == SENSOR_NEXT_CLASS:
            attributes.update(self._get_next_class_attributes(child))

        return attributes

    def _get_upcoming_tasks_attributes(self, child: ChildData) -> Dict[str, Any]:
        """Get attributes for upcoming tasks sensor."""
        overdue_tasks = child.overdue
        now = dates.get_offset_time()

        return {
            "tasks": [
                {
                    "title": task.title,
                    "subject": UNKNOWN_SUBJECT if task.subject is None else task.subject,
                    **_change_attributes(task),
                    "due_date": dates.local_midnight(task.due).isoformat() if task.due else None,
                    "due_date_formatted": (task.due.strftime("%A, %d %B %Y") if task.due else None),
                    "days_until_due": ((task.due - now.date()).days if task.due else None),
                    "setter": task.setter,
                }
                for task in child.upcoming
            ],
            "overdue_count": len(overdue_tasks),
            "overdue_tasks": [
                {
                    "title": task.title,
                    "subject": UNKNOWN_SUBJECT if task.subject is None else task.subject,
                    **_change_attributes(task),
                    "due_date_formatted": (task.due.strftime("%A, %d %B %Y") if task.due else None),
                    "days_overdue": ((now.date() - task.due).days if task.due else 0),
                }
                for task in overdue_tasks
            ],
        }

    def _get_tasks_due_today_attributes(self, child: ChildData) -> Dict[str, Any]:
        """Get attributes for tasks due today sensor."""
        return {
            "tasks": [
                {
                    "title": task.title,
                    "subject": UNKNOWN_SUBJECT if task.subject is None else task.subject,
                    **_change_attributes(task),
                    "setter": task.setter,
                    "description": _description(task),
                }
                for task in child.due_today
            ],
        }

    def _get_overdue_tasks_attributes(self, child: ChildData) -> Dict[str, Any]:
        """Get attributes for overdue tasks sensor."""
        now = dates.get_offset_time()

        return {
            "tasks": [
                {
                    "title": task.title,
                    "subject": UNKNOWN_SUBJECT if task.subject is None else task.subject,
                    **_change_attributes(task),
                    "due_date": dates.local_midnight(task.due).isoformat() if task.due else None,
                    "due_date_formatted": (task.due.strftime("%A, %d %B %Y") if task.due else None),
                    "days_overdue": ((now.date() - task.due).days if task.due else 0),
                    "setter": task.setter,
                    "description": _description(task),
                }
                for task in child.overdue
            ],
        }

    def _get_current_class_subject(self, child: ChildData) -> Optional[str]:
        """Get the current class subject without time prefix."""
        events = child.lessons
        if not events:
            return "None"

        now = dates.get_offset_time()

        # Find current event (class currently happening)
        for event in events:
            if event.start <= now <= event.end:
                return event.subject

        # If no current class, return "None" string
        return "None"

    def _get_current_class(self, child: ChildData) -> Optional[str]:
        """Get the current class if one is active, otherwise return None."""
        events = child.lessons
        if not events:
            return "None"

        now = dates.get_offset_time()

        # Get show_class_times option
        show_times = entry_option(self._config_entry, CONF_SHOW_CLASS_TIMES, DEFAULT_SHOW_CLASS_TIMES)

        # Find current event (class currently happening)
        for event in events:
            if event.start <= now <= event.end:
                subject = event.subject
                if show_times:
                    # Convert to local timezone before formatting
                    start_local = dt_util.as_local(event.start)
                    end_local = dt_util.as_local(event.end)
                    # Format times as H.MM (no leading zeros on hours)
                    start_time = f"{start_local.hour}.{start_local.minute:02d}"
                    end_time = f"{end_local.hour}.{end_local.minute:02d}"
                    return f"{start_time}-{end_time}: {subject}"
                return subject

        # If no current class, return "None" string
        return "None"

    def _format_class_with_time(self, event: Lesson, show_times: bool) -> str | None:
        """Format a class event with optional time prefix."""
        subject = event.subject
        if not show_times:
            return subject

        # Convert to local timezone before formatting
        start_local = dt_util.as_local(event.start)
        end_local = dt_util.as_local(event.end)
        # Format times as H.MM (no leading zeros on hours)
        start_time = f"{start_local.hour}.{start_local.minute:02d}"
        end_time = f"{end_local.hour}.{end_local.minute:02d}"
        return f"{start_time}-{end_time}: {subject}"

    def _get_next_class(self, child: ChildData) -> Optional[str]:
        """Get the next upcoming class."""
        events = child.lessons
        if not events:
            return "None"

        now = dates.get_offset_time()
        show_times = entry_option(self._config_entry, CONF_SHOW_CLASS_TIMES, DEFAULT_SHOW_CLASS_TIMES)

        # Check if we're currently in a class
        current_class_raw = self._get_current_class_subject(child)
        if current_class_raw and current_class_raw != "None":
            return self._find_next_class_after_current(events, now, show_times)

        # Not in a class - find the next upcoming class
        return self._find_next_upcoming_class(events, now, show_times)

    def _find_next_class_after_current(self, events: Sequence[Lesson], now: datetime, show_times: bool) -> str | None:
        """Find the next class when currently in a class."""
        current_date = now.date()

        for event in events:
            event_start = event.start
            if event_start > now:
                event_local = event_start.astimezone(now.tzinfo) if now.tzinfo else event_start.replace(tzinfo=None)
                if event_local.date() == current_date:
                    return self._format_class_with_time(event, show_times)
                # Next class is tomorrow
                return "None"

        return "None"

    def _find_next_upcoming_class(self, events: Sequence[Lesson], now: datetime, show_times: bool) -> str | None:
        """Find the next upcoming class when not currently in a class."""
        upcoming_events = [event for event in events if event.start > now]

        if upcoming_events:
            return self._format_class_with_time(upcoming_events[0], show_times)

        return "None"

    def _get_current_class_attributes(self, child: ChildData) -> Dict[str, Any]:
        """Get attributes for current class sensor."""
        events = child.lessons
        now = dates.get_offset_time()

        if not events:
            return {
                "status": "no_current_class",
                "current_time": now.isoformat(),
            }

        # Find current event
        current_event = None
        for event in events:
            if event.start <= now <= event.end:
                current_event = event
                break

        if not current_event:
            return {
                "status": "no_current_class",
                "current_time": now.isoformat(),
            }

        # Calculate time remaining in current class
        time_remaining = (current_event.end - now).total_seconds() / 60  # minutes

        return {
            "status": "in_class",
            "class_name": current_event.subject,
            "location": current_event.location,
            "start_time": current_event.start.isoformat(),
            "end_time": current_event.end.isoformat(),
            "minutes_remaining": round(time_remaining),
            "description": current_event.description,
            "current_time": now.isoformat(),
        }

    def _get_next_class_attributes(self, child: ChildData) -> Dict[str, Any]:
        """Get attributes for next class sensor."""
        events = child.lessons
        now = dates.get_offset_time()

        if not events:
            return {"status": "no_upcoming_class", "current_time": now.isoformat()}

        upcoming_events = self._get_upcoming_events(events, now)
        if not upcoming_events:
            return {"status": "no_upcoming_class", "current_time": now.isoformat()}

        next_event = upcoming_events[0]
        return self._build_next_class_attributes(next_event, now, child)

    def _get_upcoming_events(self, events: Sequence[Lesson], now: datetime) -> List[Lesson]:
        """Get list of upcoming events after the current time."""
        upcoming_events = []
        for event in events:
            if event.start > now:
                upcoming_events.append(event)
        return upcoming_events

    def _build_next_class_attributes(self, next_event: Lesson, now: datetime, child: ChildData) -> Dict[str, Any]:
        """Build attributes dict for next class sensor."""
        current_class = self._get_current_class(child)
        event_start = next_event.start
        event_local = event_start.astimezone(now.tzinfo) if now.tzinfo else event_start.replace(tzinfo=None)
        is_today = now.date() == event_local.date()

        context = self._determine_next_class_context(current_class, is_today)

        if context == "last_class_of_day":
            return {
                "status": "last_class_of_day",
                "current_time": now.isoformat(),
                "context": "no_more_classes_today",
            }

        time_until = (event_start - now).total_seconds() / 60

        return {
            "status": "class_scheduled",
            "class_name": next_event.subject,
            "location": next_event.location,
            "start_time": next_event.start.isoformat(),
            "end_time": next_event.end.isoformat(),
            "minutes_until": round(time_until),
            "description": next_event.description,
            "current_time": now.isoformat(),
            "context": context,
        }

    @staticmethod
    def _determine_next_class_context(current_class: Optional[str], is_today: bool) -> str:
        """Determine the context for the next class."""
        in_class = current_class and current_class != "None"

        if in_class and is_today:
            return "next_class_today"
        if in_class and not is_today:
            return "last_class_of_day"
        if not in_class and is_today:
            return "next_class_today"
        return "next_class_future_day"
