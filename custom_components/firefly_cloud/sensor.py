"""Sensor platform for Firefly Cloud integration."""
from datetime import datetime, timedelta
import logging
from typing import Any, Dict, List, Optional

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_SCHOOL_NAME,
    CONF_USER_GUID,
    DOMAIN,
    SENSOR_TASKS_DUE_TODAY,
    SENSOR_TODAY_SCHEDULE,
    SENSOR_TYPES,
    SENSOR_UPCOMING_TASKS,
    SENSOR_WEEK_SCHEDULE,
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
    
    # Create sensors for each type
    entities: List[SensorEntity] = []
    
    for sensor_type in SENSOR_TYPES:
        entities.append(
            FireflySensor(
                coordinator=coordinator,
                config_entry=config_entry,
                sensor_type=sensor_type,
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
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._sensor_type = sensor_type
        self._sensor_config = SENSOR_TYPES[sensor_type]
        
        # Generate unique entity ID
        school_name = config_entry.data.get(CONF_SCHOOL_NAME, "firefly")
        self._attr_unique_id = f"{config_entry.entry_id}_{sensor_type}"
        
        # Set entity properties
        self._attr_name = f"{school_name} {self._sensor_config['name']}"
        self._attr_icon = self._sensor_config["icon"]
        self._attr_native_unit_of_measurement = self._sensor_config["unit"]
        self._attr_device_class = self._sensor_config["device_class"]

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
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
        )

    @property
    def native_value(self) -> Optional[int]:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        try:
            if self._sensor_type == SENSOR_TODAY_SCHEDULE:
                return len(self.coordinator.data.get("events", {}).get("today", []))
            elif self._sensor_type == SENSOR_WEEK_SCHEDULE:
                return len(self.coordinator.data.get("events", {}).get("week", []))
            elif self._sensor_type == SENSOR_UPCOMING_TASKS:
                return len(self.coordinator.data.get("tasks", {}).get("upcoming", []))
            elif self._sensor_type == SENSOR_TASKS_DUE_TODAY:
                return len(self.coordinator.data.get("tasks", {}).get("due_today", []))
        except (KeyError, TypeError, AttributeError):
            return 0

        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return {}

        attributes = {
            "last_updated": self.coordinator.data.get("last_updated"),
        }

        if self._sensor_type == SENSOR_TODAY_SCHEDULE:
            attributes.update(self._get_today_schedule_attributes())
        elif self._sensor_type == SENSOR_WEEK_SCHEDULE:
            attributes.update(self._get_week_schedule_attributes())
        elif self._sensor_type == SENSOR_UPCOMING_TASKS:
            attributes.update(self._get_upcoming_tasks_attributes())
        elif self._sensor_type == SENSOR_TASKS_DUE_TODAY:
            attributes.update(self._get_tasks_due_today_attributes())

        return attributes

    def _get_today_schedule_attributes(self) -> Dict[str, Any]:
        """Get attributes for today's schedule sensor."""
        events = self.coordinator.data.get("events", {}).get("today", [])
        
        # Check if coordinator has the method before calling it
        if hasattr(self.coordinator, 'get_special_requirements_today'):
            special_requirements = self.coordinator.get_special_requirements_today()
        else:
            special_requirements = []
        
        # Current and next class
        now = datetime.now()
        current_class = None
        next_class = None
        
        for event in events:
            if event["start"] <= now <= event["end"]:
                current_class = event
            elif event["start"] > now and next_class is None:
                next_class = event
        
        attributes = {
            "classes": [
                {
                    "start_time": event["start"].strftime("%H:%M"),
                    "end_time": event["end"].strftime("%H:%M"),
                    "subject": event["subject"],
                    "location": event.get("location"),
                    "description": event.get("description"),
                }
                for event in events
            ],
            "special_requirements": special_requirements,
            "current_class": (
                {
                    "subject": current_class["subject"],
                    "start_time": current_class["start"].strftime("%H:%M"),
                    "end_time": current_class["end"].strftime("%H:%M"),
                    "location": current_class.get("location"),
                }
                if current_class
                else None
            ),
            "next_class": (
                {
                    "subject": next_class["subject"],
                    "start_time": next_class["start"].strftime("%H:%M"),
                    "location": next_class.get("location"),
                }
                if next_class
                else None
            ),
        }
        
        return attributes

    def _get_week_schedule_attributes(self) -> Dict[str, Any]:
        """Get attributes for week schedule sensor."""
        events = self.coordinator.data.get("events", {}).get("week", [])
        
        # Group events by day
        schedule_by_day = {}
        today = datetime.now().date()
        
        for i in range(7):
            day_date = today + timedelta(days=i)
            day_name = day_date.strftime("%A")
            day_events = [
                event for event in events
                if event["start"].date() == day_date
            ]
            
            schedule_by_day[day_name] = [
                {
                    "start_time": event["start"].strftime("%H:%M"),
                    "end_time": event["end"].strftime("%H:%M"),
                    "subject": event["subject"],
                    "location": event.get("location"),
                }
                for event in day_events
            ]
        
        # Identify special days (with requirements)
        special_days = []
        for day_name, day_events in schedule_by_day.items():
            for event in day_events:
                subject = event["subject"].lower()
                if any(keyword in subject for keyword in ["pe", "sport", "games", "physical"]):
                    special_days.append(f"{day_name}: Sports kit required")
        
        return {
            "schedule_by_day": schedule_by_day,
            "special_days": list(set(special_days)),
            "total_classes_this_week": len(events),
        }

    def _get_upcoming_tasks_attributes(self) -> Dict[str, Any]:
        """Get attributes for upcoming tasks sensor."""
        tasks = self.coordinator.data.get("tasks", {}).get("upcoming", [])
        overdue_tasks = self.coordinator.data.get("tasks", {}).get("overdue", [])
        
        # Group tasks by subject
        if hasattr(self.coordinator, 'get_tasks_by_subject'):
            tasks_by_subject = self.coordinator.get_tasks_by_subject()
        else:
            tasks_by_subject = {}
        
        # Group tasks by due date
        tasks_by_due_date = {}
        for task in tasks:
            if task["due_date"]:
                due_date_str = task["due_date"].strftime("%Y-%m-%d")
                if due_date_str not in tasks_by_due_date:
                    tasks_by_due_date[due_date_str] = []
                tasks_by_due_date[due_date_str].append({
                    "title": task["title"],
                    "subject": task["subject"],
                    "task_type": task["task_type"],
                })
        
        return {
            "tasks": [
                {
                    "title": task["title"],
                    "subject": task["subject"],
                    "due_date": task["due_date"].isoformat() if task["due_date"] else None,
                    "due_date_formatted": (
                        task["due_date"].strftime("%A, %d %B %Y")
                        if task["due_date"]
                        else None
                    ),
                    "task_type": task["task_type"],
                    "days_until_due": (
                        (task["due_date"].date() - datetime.now().date()).days
                        if task["due_date"]
                        else None
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
                            task["due_date"].strftime("%A, %d %B")
                            if task["due_date"]
                            else "No due date"
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
                    "due_date_formatted": (
                        task["due_date"].strftime("%A, %d %B %Y")
                        if task["due_date"]
                        else None
                    ),
                    "days_overdue": (
                        (datetime.now().date() - task["due_date"].date()).days
                        if task["due_date"]
                        else 0
                    ),
                }
                for task in overdue_tasks
            ],
        }

    def _get_tasks_due_today_attributes(self) -> Dict[str, Any]:
        """Get attributes for tasks due today sensor."""
        tasks = self.coordinator.data.get("tasks", {}).get("due_today", [])
        
        # Categorize by urgency/type
        urgent_tasks = [
            task for task in tasks
            if task["task_type"] in ["test", "project"] or "urgent" in task["title"].lower()
        ]
        
        return {
            "tasks": [
                {
                    "title": task["title"],
                    "subject": task["subject"],
                    "task_type": task["task_type"],
                    "setter": task["setter"],
                    "description": task["description"][:100] + "..." if len(task["description"]) > 100 else task["description"],
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