"""Todo platform for Firefly Cloud integration."""

from datetime import datetime, date
from typing import Any, Dict, List, Optional

from homeassistant.components.todo import (
    TodoItem,
    TodoListEntity,
)
from homeassistant.components.todo.const import (
    TodoItemStatus,
    TodoListEntityFeature,
)
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
)
from .coordinator import FireflyUpdateCoordinator



async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firefly Cloud todo platform."""
    coordinator: FireflyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Get children GUIDs from config or use user GUID if no children
    children_guids = config_entry.data.get(CONF_CHILDREN_GUIDS, [])
    if not children_guids:
        children_guids = [config_entry.data[CONF_USER_GUID]]

    # Create todo list for each child
    entities: List[TodoListEntity] = []

    for child_guid in children_guids:
        entities.append(
            FireflyTodoListEntity(
                coordinator=coordinator,
                config_entry=config_entry,
                child_guid=child_guid,
            )
        )

    async_add_entities(entities)


class FireflyTodoListEntity(CoordinatorEntity, TodoListEntity):  # pylint: disable=too-many-instance-attributes
    """Firefly todo list entity."""

    def __init__(
        self,
        coordinator: FireflyUpdateCoordinator,
        config_entry: ConfigEntry,
        child_guid: str,
    ) -> None:
        """Initialize the todo list entity."""
        super().__init__(coordinator)
        self._config_entry = config_entry
        self._child_guid = child_guid

        # Generate unique entity ID
        school_name = config_entry.data.get(CONF_SCHOOL_NAME, "firefly")
        self._attr_unique_id = f"{config_entry.entry_id}_todo_{child_guid}"

        # Set entity properties - will be updated with child name when data is available
        self._base_name = f"{school_name} Tasks"
        self._attr_name = f"{self._base_name} ({child_guid[:8]})"
        self._attr_icon = "mdi:clipboard-check"

        # Device info for grouping
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"Firefly Cloud - {school_name}",
            manufacturer="Firefly Learning",
            model="Firefly Cloud Integration",
            sw_version="1.0.0",
            configuration_url=config_entry.data.get("host"),
        )

        # Todo list features - Firefly is read-only, so we only support viewing  # pylint: disable=line-too-long
        self._attr_supported_features = TodoListEntityFeature(0)  # Read-only

    @property
    def name(self) -> str:
        """Return the display name of the todo list."""
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
    def todo_items(self) -> Optional[List[TodoItem]]:
        """Return the todo items."""
        if not self.coordinator.data:
            return None

        # Get data for this specific child
        children_data = self.coordinator.data.get("children_data", {})

        if self._child_guid not in children_data:
            return None

        child_data = children_data[self._child_guid]
        tasks = child_data.get("tasks", {})

        todo_items = []

        # Add upcoming tasks
        upcoming_tasks = tasks.get("upcoming", [])
        for task in upcoming_tasks:
            status = self._map_completion_status(task.get("completionStatus", "Todo"))
            todo_items.append(self._create_todo_item(task, status))

        # Add overdue tasks
        overdue_tasks = tasks.get("overdue", [])
        for task in overdue_tasks:
            status = self._map_completion_status(task.get("completionStatus", "Todo"))
            todo_items.append(self._create_todo_item(task, status))

        # Add tasks due today
        due_today_tasks = tasks.get("due_today", [])
        for task in due_today_tasks:
            status = self._map_completion_status(task.get("completionStatus", "Todo"))
            todo_items.append(self._create_todo_item(task, status))

        return todo_items

    def _map_completion_status(self, completion_status: str) -> TodoItemStatus:
        """Map Firefly completion status to TodoItemStatus."""
        if completion_status == "Done":
            return TodoItemStatus.COMPLETED
        return TodoItemStatus.NEEDS_ACTION

    def _create_todo_item(self, task_data: Dict[str, Any], status: TodoItemStatus) -> TodoItem:
        """Create a TodoItem from task data."""
        # Create unique ID from task data
        uid = f"{task_data.get('id', '')}_{task_data.get('title', '')}"
        uid = uid.replace(" ", "_").replace("/", "_")[:50]  # Limit length and sanitize

        # Use task title directly without subject prefix
        title = task_data.get("title", "Untitled Task")
        summary = title

        # Handle due date - convert date to datetime if needed
        due = None
        if task_data.get("due_date"):
            due_date = task_data["due_date"]
            if isinstance(due_date, datetime):
                due = due_date
            elif isinstance(due_date, date):
                # Convert date to datetime at midnight
                due = datetime.combine(due_date, datetime.min.time())

        # Create description with additional details
        description_parts = []
        if task_data.get("task_type"):
            description_parts.append(f"Type: {task_data['task_type']}")
        if task_data.get("setter"):
            description_parts.append(f"Set by: {task_data['setter']}")
        if task_data.get("description"):
            description_parts.append(task_data["description"])

        description = "\n".join(description_parts) if description_parts else None

        return TodoItem(
            uid=uid,
            summary=summary,
            status=status,
            due=due,
            description=description,
        )

    async def async_create_todo_item(self, item: TodoItem) -> None:  # pylint: disable=unused-argument
        """Create a new todo item."""
        raise NotImplementedError("Firefly Cloud integration is read-only")

    async def async_delete_todo_items(self, uids: list[str]) -> None:  # pylint: disable=unused-argument
        """Delete todo items."""
        raise NotImplementedError("Firefly Cloud integration is read-only")

    async def async_update_todo_item(self, item: TodoItem) -> None:  # pylint: disable=unused-argument
        """Update a todo item."""
        raise NotImplementedError("Firefly Cloud integration is read-only")

    async def async_move_todo_item(
        self,
        uid: str,  # pylint: disable=unused-argument
        previous_uid: str | None = None,  # pylint: disable=unused-argument
    ) -> None:
        """Move a todo item."""
        raise NotImplementedError("Firefly Cloud integration is read-only")
