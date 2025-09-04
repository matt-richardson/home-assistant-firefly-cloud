"""Sensor platform for Firefly Cloud integration."""

from datetime import datetime
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_CHILDREN_GUIDS,
    CONF_SCHOOL_NAME,
    CONF_USER_GUID,
    DOMAIN,
    SENSOR_TASKS_DUE_TODAY,
    SENSOR_TYPES,
    SENSOR_UPCOMING_TASKS,
)
from .coordinator import FireflyUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


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
    def native_value(self) -> Optional[int]:
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
        except (KeyError, TypeError, AttributeError):
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
                        "subject": task["subject"],
                        "task_type": task["task_type"],
                    }
                )

        return {
            "tasks": [
                {
                    "title": task["title"],
                    "subject": task["subject"],
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
                    "subject": task["subject"],
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
                    "subject": task["subject"],
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
                    "subject": task["subject"],
                    "task_type": task["task_type"],
                }
                for task in urgent_tasks
            ],
            "tasks_by_subject": {
                subject: len([t for t in tasks if t["subject"] == subject])
                for subject in set(task["subject"] for task in tasks)
            },
            "homework_count": len([t for t in tasks if t["task_type"] == "homework"]),
            "project_count": len([t for t in tasks if t["task_type"] == "project"]),
            "test_count": len([t for t in tasks if t["task_type"] == "test"]),
        }
