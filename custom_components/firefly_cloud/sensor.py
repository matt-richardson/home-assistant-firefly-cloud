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

    def _show_class_times(self) -> bool:
        return bool(entry_option(self._config_entry, CONF_SHOW_CLASS_TIMES, DEFAULT_SHOW_CLASS_TIMES))

    def _get_current_class(self, child: ChildData) -> Optional[str]:
        """Get the current class if one is active, otherwise the string "None"."""
        lesson = _current_lesson(child.lessons, dates.get_offset_time())
        if lesson is None:
            return "None"
        return _format_class(lesson, self._show_class_times())

    def _get_next_class(self, child: ChildData) -> Optional[str]:
        """Get the next class; while in class, only a later class on the same day counts."""
        now = dates.get_offset_time()
        lesson = _next_lesson(child.lessons, now)
        if lesson is None:
            return "None"
        if _current_lesson(child.lessons, now) is not None and not _is_same_day(lesson, now):
            return "None"
        return _format_class(lesson, self._show_class_times())

    @staticmethod
    def _get_current_class_attributes(child: ChildData) -> Dict[str, Any]:
        """Get attributes for current class sensor."""
        now = dates.get_offset_time()
        lesson = _current_lesson(child.lessons, now)
        if lesson is None:
            return {"status": "no_current_class", "current_time": now.isoformat()}

        return {
            "status": "in_class",
            "class_name": lesson.subject,
            "location": lesson.location,
            "start_time": lesson.start.isoformat(),
            "end_time": lesson.end.isoformat(),
            "minutes_remaining": round((lesson.end - now).total_seconds() / 60),
            "description": lesson.description,
            "current_time": now.isoformat(),
        }

    @staticmethod
    def _get_next_class_attributes(child: ChildData) -> Dict[str, Any]:
        """Get attributes for next class sensor."""
        now = dates.get_offset_time()
        lesson = _next_lesson(child.lessons, now)
        if lesson is None:
            return {"status": "no_upcoming_class", "current_time": now.isoformat()}

        is_today = _is_same_day(lesson, now)
        if _current_lesson(child.lessons, now) is not None and not is_today:
            return {
                "status": "last_class_of_day",
                "current_time": now.isoformat(),
                "context": "no_more_classes_today",
            }

        return {
            "status": "class_scheduled",
            "class_name": lesson.subject,
            "location": lesson.location,
            "start_time": lesson.start.isoformat(),
            "end_time": lesson.end.isoformat(),
            "minutes_until": round((lesson.start - now).total_seconds() / 60),
            "description": lesson.description,
            "current_time": now.isoformat(),
            "context": "next_class_today" if is_today else "next_class_future_day",
        }


def _current_lesson(lessons: Sequence[Lesson], now: datetime) -> Lesson | None:
    """Return the lesson happening now (lessons are sorted by start)."""
    return next((lesson for lesson in lessons if lesson.start <= now <= lesson.end), None)


def _next_lesson(lessons: Sequence[Lesson], now: datetime) -> Lesson | None:
    """Return the first lesson starting after now (lessons are sorted by start)."""
    return next((lesson for lesson in lessons if lesson.start > now), None)


def _is_same_day(lesson: Lesson, now: datetime) -> bool:
    return lesson.start.astimezone(now.tzinfo).date() == now.date()


def _format_class(lesson: Lesson, show_times: bool) -> str | None:
    """Return the subject, prefixed with local times as "H.MM-H.MM: " if show_times."""
    if not show_times:
        return lesson.subject
    start = dt_util.as_local(lesson.start)
    end = dt_util.as_local(lesson.end)
    return f"{start.hour}.{start.minute:02d}-{end.hour}.{end.minute:02d}: {lesson.subject}"
