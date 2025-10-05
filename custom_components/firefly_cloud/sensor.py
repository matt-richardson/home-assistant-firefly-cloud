"""Sensor platform for Firefly Cloud integration."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
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


class FireflySensor(CoordinatorEntity, SensorEntity):
    """Base Firefly sensor."""

    def __init__(
        self,
        coordinator: FireflyUpdateCoordinator,
        config_entry: ConfigEntry,
        sensor_type: str,
        child_guid: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._sensor_type = sensor_type
        self._sensor_config = SENSOR_TYPES[sensor_type]
        self._child_guid = child_guid

        # Generate unique entity ID
        school_name = config_entry.data.get(CONF_SCHOOL_NAME, "firefly")
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}_{child_guid}"

        # Set entity properties - will be updated with child name when data is available
        self._base_name = f"{school_name} {self._sensor_config['name']}"
        self._attr_name = f"{self._base_name} ({child_guid[:8]})"
        self._attr_icon = self._sensor_config["icon"]
        self._attr_native_unit_of_measurement = self._sensor_config["unit"]
        # Only set device_class if it's not None and cast to proper type
        device_class = self._sensor_config.get("device_class")
        if device_class is not None:
            # Cast to SensorDeviceClass if it's a string, otherwise use as-is
            if isinstance(device_class, str):
                try:
                    self._attr_device_class = SensorDeviceClass(device_class)
                except ValueError:
                    # If the string doesn't match any SensorDeviceClass, skip setting it
                    pass
            else:
                self._attr_device_class = device_class

        # Device info for grouping
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"Firefly Cloud - {school_name}",
            manufacturer="Firefly Learning",
            model="Firefly Cloud Integration",
            sw_version="1.0.0",
            configuration_url=config_entry.data.get("host"),
        )

    @property
    def name(self) -> str:
        """Return the display name of the sensor."""
        if self.coordinator.data and self._child_guid in self.coordinator.data.get("children_data", {}):
            child_data = self.coordinator.data["children_data"][self._child_guid]
            child_name = child_data.get("name")
            if child_name:
                return f"{self._base_name} ({child_name})"
        return self._attr_name or f"{self._base_name} ({self._child_guid[:8]})"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._child_guid in self.coordinator.data.get("children_data", {})
        )

    @property
    def native_value(self) -> Optional[str | int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        # Get data for this specific child
        children_data = self.coordinator.data.get("children_data", {})

        # Return None if child doesn't exist
        if self._child_guid not in children_data:
            return None

        child_data = children_data[self._child_guid]

        try:
            if self._sensor_type == SENSOR_UPCOMING_TASKS:
                return len(child_data.get("tasks", {}).get("upcoming", []))
            if self._sensor_type == SENSOR_TASKS_DUE_TODAY:
                return len(child_data.get("tasks", {}).get("due_today", []))
            if self._sensor_type == SENSOR_OVERDUE_TASKS:
                return len(child_data.get("tasks", {}).get("overdue", []))
            if self._sensor_type == SENSOR_CURRENT_CLASS:
                return self._get_current_class(child_data)
            if self._sensor_type == SENSOR_NEXT_CLASS:
                return self._get_next_class(child_data)
        except (KeyError, TypeError, AttributeError):
            if self._sensor_type in [SENSOR_UPCOMING_TASKS, SENSOR_TASKS_DUE_TODAY, SENSOR_OVERDUE_TASKS]:
                return 0
            return None

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
        tasks = child_data.get("tasks", {}).get("upcoming", [])
        overdue_tasks = child_data.get("tasks", {}).get("overdue", [])

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
                        (task["due_date"].date() - datetime.now().date()).days if task["due_date"] else None
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
                    "days_overdue": ((datetime.now().date() - task["due_date"].date()).days if task["due_date"] else 0),
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
        tasks = child_data.get("tasks", {}).get("overdue", [])

        return {
            "tasks": [
                {
                    "title": task["title"],
                    "subject": task.get("subject", "Unknown"),
                    "due_date": task["due_date"].isoformat() if task["due_date"] else None,
                    "due_date_formatted": (task["due_date"].strftime("%A, %d %B %Y") if task["due_date"] else None),
                    "task_type": task["task_type"],
                    "days_overdue": ((datetime.now().date() - task["due_date"].date()).days if task["due_date"] else 0),
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

    def _get_next_class(self, child_data: Dict[str, Any]) -> Optional[str]:
        """Get the next upcoming class."""
        events = child_data.get("events", {}).get("week", [])
        if not events:
            return "None"

        from .const import get_offset_time

        now = get_offset_time()
        current_date = now.date()

        # Get show_class_times option
        show_times = self._config_entry.options.get(
            CONF_SHOW_CLASS_TIMES,
            self._config_entry.data.get(CONF_SHOW_CLASS_TIMES, DEFAULT_SHOW_CLASS_TIMES),
        )

        # Check if we're currently IN a class (need to check without time prefix for comparison)
        current_class_raw = self._get_current_class_subject(child_data)
        if current_class_raw and current_class_raw != "None":
            # We're in a class - find the next class using timezone-aware comparison
            for event in events:
                event_start = event["start"]
                if hasattr(event_start, "tzinfo") and event_start.tzinfo is None:
                    event_start = dt_util.as_utc(event_start)

                if event_start > now:
                    # Convert event time to local timezone for date comparison
                    event_local = event_start.astimezone(now.tzinfo) if now.tzinfo else event_start.replace(tzinfo=None)

                    # Check if it's today in local time
                    if event_local.date() == current_date:
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
                    else:
                        return "None"  # Next class is tomorrow - last class of day

            # No upcoming events at all
            return "None"

        # We're not in a class - find the next class (today or future days)
        upcoming_events = []
        for event in events:
            event_start = event["start"]
            # Handle timezone awareness mismatch
            if hasattr(event_start, "tzinfo") and event_start.tzinfo is None:
                event_start = dt_util.as_utc(event_start)

            if event_start > now:
                upcoming_events.append(event)

        if upcoming_events:
            # Events are already sorted by start time in coordinator
            next_event = upcoming_events[0]
            subject = next_event["subject"]
            if show_times:
                # Convert to local timezone before formatting
                start_local = dt_util.as_local(next_event["start"]) if next_event["start"].tzinfo else next_event["start"]
                end_local = dt_util.as_local(next_event["end"]) if next_event["end"].tzinfo else next_event["end"]
                # Format times as H.MM (no leading zeros on hours)
                start_time = f"{start_local.hour}.{start_local.minute:02d}"
                end_time = f"{end_local.hour}.{end_local.minute:02d}"
                return f"{start_time}-{end_time}: {subject}"
            return subject

        return "None"

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
            return {
                "status": "no_upcoming_class",
                "current_time": now.isoformat(),
            }

        # Check if we're currently IN a class
        current_class = self._get_current_class(child_data)
        if current_class:
            # We're in a class - but let's use the same logic as "not in class"
            # to find the truly next class, whether today or tomorrow
            # This avoids the issue of late-night events being considered "next class today"
            pass

        # Find the next class (any day)
        upcoming_events = []
        for event in events:
            event_start = event["start"]
            # Handle timezone awareness mismatch
            if hasattr(event_start, "tzinfo") and event_start.tzinfo is None:
                event_start = dt_util.as_utc(event_start)

            if event_start > now:
                upcoming_events.append(event)

        if not upcoming_events:
            return {
                "status": "no_upcoming_class",
                "current_time": now.isoformat(),
            }

        next_event = upcoming_events[0]
        event_start = next_event["start"]

        # Convert event time to local timezone for proper date comparison
        event_local = next_event["start"]
        if hasattr(event_local, "tzinfo") and event_local.tzinfo:
            # Convert UTC time to local timezone for date comparison
            event_local = event_local.astimezone(now.tzinfo) if now.tzinfo else event_local.replace(tzinfo=None)

        # Compare dates in the same timezone (both local)
        current_date_str = now.date().isoformat()
        event_local_date_str = event_local.date().isoformat()
        is_today = current_date_str == event_local_date_str

        # Determine context based on whether we're in a class and the timing
        in_class = current_class and current_class != "None"
        if in_class and is_today:
            context = "next_class_today"
        elif in_class and not is_today:
            context = "last_class_of_day"  # In class but next class is not today
        elif not in_class and is_today:
            context = "next_class_today"
        else:
            context = "next_class_future_day"

        # Convert to UTC for time calculations
        if hasattr(event_start, "tzinfo") and event_start.tzinfo is None:
            event_start = dt_util.as_utc(event_start)
        time_until = (event_start - now).total_seconds() / 60  # minutes

        # Special handling for "last class of day" scenario
        if context == "last_class_of_day":
            return {
                "status": "last_class_of_day",
                "current_time": now.isoformat(),
                "context": "no_more_classes_today",
            }

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
