"""Sensor platform for Firefly Cloud integration."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import (
    CONF_CHILDREN_GUIDS,
    CONF_SCHOOL_NAME,
    CONF_SHOW_CLASS_TIMES,
    CONF_USER_GUID,
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


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firefly Cloud sensor platform."""
    coordinator: FireflyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Get children GUIDs from config or use user GUID if no children
    children_guids = config_entry.data.get(CONF_CHILDREN_GUIDS, [])
    if not children_guids:
        children_guids = [config_entry.data[CONF_USER_GUID]]

    # Create sensors for each child and each sensor type
    entities: List[SensorEntity] = []

    for child_guid in children_guids:
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
        school_name = config_entry.data.get(CONF_SCHOOL_NAME, "firefly")
        sensor_config = SENSOR_TYPES[sensor_type]
        base_name = f"{school_name} {sensor_config['name']}"

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
        child_data = self._get_child_data()
        if not child_data:
            return None

        return self._calculate_sensor_value(child_data)

    def _calculate_sensor_value(self, child_data: Dict[str, Any]) -> Optional[str | int]:
        """Calculate the sensor value based on sensor type."""
        try:
            task_count_sensors = {
                SENSOR_UPCOMING_TASKS: "upcoming",
                SENSOR_TASKS_DUE_TODAY: "due_today",
                SENSOR_OVERDUE_TASKS: "overdue",
            }

            if self._sensor_type in task_count_sensors:
                task_type = task_count_sensors[self._sensor_type]
                return len(child_data.get("tasks", {}).get(task_type, []))

            if self._sensor_type == SENSOR_CURRENT_CLASS:
                return self._get_current_class(child_data)

            if self._sensor_type == SENSOR_NEXT_CLASS:
                return self._get_next_class(child_data)

        except (KeyError, TypeError, AttributeError):
            if self._sensor_type in [SENSOR_UPCOMING_TASKS, SENSOR_TASKS_DUE_TODAY, SENSOR_OVERDUE_TASKS]:
                return 0

        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        # Get data for this specific child
        child_data = self.coordinator.data.get("children_data", {}).get(self._child_guid, {})

        attributes = {
            "last_updated": self.coordinator.data.get("last_updated"),
            "child_guid": self._child_guid,
        }

        if self._sensor_type == SENSOR_UPCOMING_TASKS:
            attributes.update(self._get_upcoming_tasks_attributes(child_data))
        elif self._sensor_type == SENSOR_TASKS_DUE_TODAY:
            attributes.update(self._get_tasks_due_today_attributes(child_data))
        elif self._sensor_type == SENSOR_OVERDUE_TASKS:
            attributes.update(self._get_overdue_tasks_attributes(child_data))
        elif self._sensor_type == SENSOR_CURRENT_CLASS:
            attributes.update(self._get_current_class_attributes(child_data))
        elif self._sensor_type == SENSOR_NEXT_CLASS:
            attributes.update(self._get_next_class_attributes(child_data))

        return attributes

    def _get_upcoming_tasks_attributes(self, child_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get attributes for upcoming tasks sensor."""
        from .const import get_offset_time

        tasks = child_data.get("tasks", {}).get("upcoming", [])
        overdue_tasks = child_data.get("tasks", {}).get("overdue", [])
        now = get_offset_time()

        # Group tasks by subject - simplified since the method doesn't exist
        tasks_by_subject: Dict[str, List[Dict[str, Any]]] = {}
        for task in tasks:
            subject = task.get("subject", "Unknown")
            if subject not in tasks_by_subject:
                tasks_by_subject[subject] = []
            tasks_by_subject[subject].append(task)

        # Group tasks by due date
        tasks_by_due_date: Dict[str, List[Dict[str, Any]]] = {}
        for task in tasks:
            if task["due_date"]:
                due_date_str = task["due_date"].strftime("%Y-%m-%d")
                if due_date_str not in tasks_by_due_date:
                    tasks_by_due_date[due_date_str] = []
                tasks_by_due_date[due_date_str].append(
                    {
                        "title": task["title"],
                        "subject": task.get("subject", "Unknown"),
                        "task_type": task["task_type"],
                    }
                )

        return {
            "tasks": [
                {
                    "title": task["title"],
                    "subject": task.get("subject", "Unknown"),
                    "due_date": task["due_date"].isoformat() if task["due_date"] else None,
                    "due_date_formatted": (task["due_date"].strftime("%A, %d %B %Y") if task["due_date"] else None),
                    "task_type": task["task_type"],
                    "days_until_due": (
                        (task["due_date"].date() - now.date()).days if task["due_date"] else None
                    ),
                    "setter": task["setter"],
                }
                for task in tasks
            ],
            "tasks_by_subject": {
                subject: [
                    {
                        "title": task["title"],
                        "due_date_formatted": (
                            task["due_date"].strftime("%A, %d %B") if task["due_date"] else "No due date"
                        ),
                        "task_type": task["task_type"],
                    }
                    for task in subject_tasks
                ]
                for subject, subject_tasks in tasks_by_subject.items()
            },
            "tasks_by_due_date": tasks_by_due_date,
            "overdue_count": len(overdue_tasks),
            "overdue_tasks": [
                {
                    "title": task["title"],
                    "subject": task.get("subject", "Unknown"),
                    "due_date_formatted": (task["due_date"].strftime("%A, %d %B %Y") if task["due_date"] else None),
                    "days_overdue": ((now.date() - task["due_date"].date()).days if task["due_date"] else 0),
                }
                for task in overdue_tasks
            ],
        }

    def _get_tasks_due_today_attributes(self, child_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get attributes for tasks due today sensor."""
        tasks = child_data.get("tasks", {}).get("due_today", [])

        # Categorize by urgency/type
        urgent_tasks = [
            task for task in tasks if task["task_type"] in ["test", "project"] or "urgent" in task["title"].lower()
        ]

        return {
            "tasks": [
                {
                    "title": task["title"],
                    "subject": task.get("subject", "Unknown"),
                    "task_type": task["task_type"],
                    "setter": task["setter"],
                    "description": (
                        task["description"][:100] + "..."
                        if task["description"] and len(task["description"]) > 100
                        else task["description"]
                    ),
                }
                for task in tasks
            ],
            "urgent_tasks": [
                {
                    "title": task["title"],
                    "subject": task.get("subject", "Unknown"),
                    "task_type": task["task_type"],
                }
                for task in urgent_tasks
            ],
            "tasks_by_subject": {
                subject: len([t for t in tasks if t.get("subject", "Unknown") == subject])
                for subject in set(task.get("subject", "Unknown") for task in tasks)
            },
            "homework_count": len([t for t in tasks if t["task_type"] == "homework"]),
            "project_count": len([t for t in tasks if t["task_type"] == "project"]),
            "test_count": len([t for t in tasks if t["task_type"] == "test"]),
        }

    def _get_overdue_tasks_attributes(self, child_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get attributes for overdue tasks sensor."""
        from .const import get_offset_time

        tasks = child_data.get("tasks", {}).get("overdue", [])
        now = get_offset_time()

        return {
            "tasks": [
                {
                    "title": task["title"],
                    "subject": task.get("subject", "Unknown"),
                    "due_date": task["due_date"].isoformat() if task["due_date"] else None,
                    "due_date_formatted": (task["due_date"].strftime("%A, %d %B %Y") if task["due_date"] else None),
                    "task_type": task["task_type"],
                    "days_overdue": ((now.date() - task["due_date"].date()).days if task["due_date"] else 0),
                    "setter": task["setter"],
                    "description": (
                        task["description"][:100] + "..."
                        if task["description"] and len(task["description"]) > 100
                        else task["description"]
                    ),
                }
                for task in tasks
            ],
        }

    def _get_current_class_subject(self, child_data: Dict[str, Any]) -> Optional[str]:
        """Get the current class subject without time prefix."""
        events = child_data.get("events", {}).get("week", [])
        if not events:
            return "None"

        from .const import get_offset_time

        now = get_offset_time()

        # Find current event (class currently happening)
        for event in events:
            event_start = event["start"]
            event_end = event["end"]

            # Handle timezone awareness mismatch
            if hasattr(event_start, "tzinfo") and event_start.tzinfo is None:
                event_start = dt_util.as_utc(event_start)
            if hasattr(event_end, "tzinfo") and event_end.tzinfo is None:
                event_end = dt_util.as_utc(event_end)

            if event_start <= now <= event_end:
                return event["subject"]

        # If no current class, return "None" string
        return "None"

    def _get_current_class(self, child_data: Dict[str, Any]) -> Optional[str]:
        """Get the current class if one is active, otherwise return None."""
        events = child_data.get("events", {}).get("week", [])
        if not events:
            return "None"

        from .const import get_offset_time

        now = get_offset_time()

        # Get show_class_times option
        show_times = self._config_entry.options.get(
            CONF_SHOW_CLASS_TIMES,
            self._config_entry.data.get(CONF_SHOW_CLASS_TIMES, DEFAULT_SHOW_CLASS_TIMES),
        )

        # Find current event (class currently happening)
        for event in events:
            event_start = event["start"]
            event_end = event["end"]

            # Handle timezone awareness mismatch
            if hasattr(event_start, "tzinfo") and event_start.tzinfo is None:
                event_start = dt_util.as_utc(event_start)
            if hasattr(event_end, "tzinfo") and event_end.tzinfo is None:
                event_end = dt_util.as_utc(event_end)

            if event_start <= now <= event_end:
                subject = event["subject"]
                if show_times:
                    # Convert to local timezone before formatting
                    start_local = dt_util.as_local(event["start"]) if event["start"].tzinfo else event["start"]
                    end_local = dt_util.as_local(event["end"]) if event["end"].tzinfo else event["end"]
                    # Format times as H.MM (no leading zeros on hours)
                    start_time = f"{start_local.hour}.{start_local.minute:02d}"
                    end_time = f"{end_local.hour}.{end_local.minute:02d}"
                    return f"{start_time}-{end_time}: {subject}"
                return subject

        # If no current class, return "None" string
        return "None"

    def _format_class_with_time(self, event: Dict[str, Any], show_times: bool) -> str:
        """Format a class event with optional time prefix."""
        subject = event["subject"]
        if not show_times:
            return subject

        # Convert to local timezone before formatting
        start_local = dt_util.as_local(event["start"]) if event["start"].tzinfo else event["start"]
        end_local = dt_util.as_local(event["end"]) if event["end"].tzinfo else event["end"]
        # Format times as H.MM (no leading zeros on hours)
        start_time = f"{start_local.hour}.{start_local.minute:02d}"
        end_time = f"{end_local.hour}.{end_local.minute:02d}"
        return f"{start_time}-{end_time}: {subject}"

    def _get_next_class(self, child_data: Dict[str, Any]) -> Optional[str]:
        """Get the next upcoming class."""
        events = child_data.get("events", {}).get("week", [])
        if not events:
            return "None"

        from .const import get_offset_time

        now = get_offset_time()
        show_times = self._config_entry.options.get(
            CONF_SHOW_CLASS_TIMES,
            self._config_entry.data.get(CONF_SHOW_CLASS_TIMES, DEFAULT_SHOW_CLASS_TIMES),
        )

        # Check if we're currently in a class
        current_class_raw = self._get_current_class_subject(child_data)
        if current_class_raw and current_class_raw != "None":
            return self._find_next_class_after_current(events, now, show_times)

        # Not in a class - find the next upcoming class
        return self._find_next_upcoming_class(events, now, show_times)

    def _find_next_class_after_current(self, events: List[Dict[str, Any]], now: datetime, show_times: bool) -> str:
        """Find the next class when currently in a class."""
        current_date = now.date()

        for event in events:
            event_start = self._normalize_event_time(event["start"])
            if event_start > now:
                event_local = event_start.astimezone(now.tzinfo) if now.tzinfo else event_start.replace(tzinfo=None)
                if event_local.date() == current_date:
                    return self._format_class_with_time(event, show_times)
                # Next class is tomorrow
                return "None"

        return "None"

    def _find_next_upcoming_class(self, events: List[Dict[str, Any]], now: datetime, show_times: bool) -> str:
        """Find the next upcoming class when not currently in a class."""
        upcoming_events = [event for event in events if self._normalize_event_time(event["start"]) > now]

        if upcoming_events:
            return self._format_class_with_time(upcoming_events[0], show_times)

        return "None"

    @staticmethod
    def _normalize_event_time(event_time: datetime) -> datetime:
        """Normalize event time to be timezone-aware."""
        if hasattr(event_time, "tzinfo") and event_time.tzinfo is None:
            return dt_util.as_utc(event_time)
        return event_time

    def _get_current_class_attributes(self, child_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get attributes for current class sensor."""
        events = child_data.get("events", {}).get("week", [])
        from .const import get_offset_time

        now = get_offset_time()

        if not events:
            return {
                "status": "no_current_class",
                "current_time": now.isoformat(),
            }

        # Find current event
        current_event = None
        for event in events:
            event_start = event["start"]
            event_end = event["end"]

            # Handle timezone awareness mismatch
            if hasattr(event_start, "tzinfo") and event_start.tzinfo is None:
                event_start = dt_util.as_utc(event_start)
            if hasattr(event_end, "tzinfo") and event_end.tzinfo is None:
                event_end = dt_util.as_utc(event_end)

            if event_start <= now <= event_end:
                current_event = event
                break

        if not current_event:
            return {
                "status": "no_current_class",
                "current_time": now.isoformat(),
            }

        # Calculate time remaining in current class
        event_end = current_event["end"]
        if hasattr(event_end, "tzinfo") and event_end.tzinfo is None:
            event_end = dt_util.as_utc(event_end)
        time_remaining = (event_end - now).total_seconds() / 60  # minutes

        return {
            "status": "in_class",
            "class_name": current_event["subject"],
            "location": current_event.get("location"),
            "start_time": current_event["start"].isoformat(),
            "end_time": current_event["end"].isoformat(),
            "minutes_remaining": round(time_remaining),
            "description": current_event.get("description"),
            "current_time": now.isoformat(),
        }

    def _get_next_class_attributes(self, child_data: Dict[str, Any]) -> Dict[str, Any]:
        """Get attributes for next class sensor."""
        events = child_data.get("events", {}).get("week", [])
        from .const import get_offset_time

        now = get_offset_time()

        if not events:
            return {"status": "no_upcoming_class", "current_time": now.isoformat()}

        upcoming_events = self._get_upcoming_events(events, now)
        if not upcoming_events:
            return {"status": "no_upcoming_class", "current_time": now.isoformat()}

        next_event = upcoming_events[0]
        return self._build_next_class_attributes(next_event, now, child_data)

    def _get_upcoming_events(self, events: List[Dict[str, Any]], now: datetime) -> List[Dict[str, Any]]:
        """Get list of upcoming events after the current time."""
        upcoming_events = []
        for event in events:
            event_start = self._normalize_event_time(event["start"])
            if event_start > now:
                upcoming_events.append(event)
        return upcoming_events

    def _build_next_class_attributes(
        self, next_event: Dict[str, Any], now: datetime, child_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Build attributes dict for next class sensor."""
        current_class = self._get_current_class(child_data)
        event_start = self._normalize_event_time(next_event["start"])
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
            "class_name": next_event["subject"],
            "location": next_event.get("location"),
            "start_time": next_event["start"].isoformat(),
            "end_time": next_event["end"].isoformat(),
            "minutes_until": round(time_until),
            "description": next_event.get("description"),
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
