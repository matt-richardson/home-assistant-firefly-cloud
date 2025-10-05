"""Todo platform for Firefly Cloud integration."""

from datetime import date, datetime
from typing import Any, Dict, List

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
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_CHILDREN_GUIDS,
    CONF_SCHOOL_NAME,
    CONF_USER_GUID,
    DOMAIN,
)
from .coordinator import FireflyUpdateCoordinator
from .entity import FireflyBaseEntity


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


class FireflyTodoListEntity(FireflyBaseEntity, TodoListEntity):
    """Firefly todo list entity."""

    def __init__(
        self,
        coordinator: FireflyUpdateCoordinator,
        config_entry: ConfigEntry,
        child_guid: str,
    ) -> None:
        """Initialize the todo list entity."""
        school_name = config_entry.data.get(CONF_SCHOOL_NAME, "firefly")
        base_name = f"{school_name} Tasks"

        super().__init__(coordinator, config_entry, child_guid, base_name)

        self._config_entry = config_entry

        # Generate unique entity ID
        self._attr_unique_id = f"{config_entry.entry_id}_todo_{child_guid}"

        # Set entity properties
        self._attr_icon = "mdi:clipboard-check"

        # Firefly is read-only, so we only support viewing (no creation/editing/deletion)
        self._attr_supported_features = TodoListEntityFeature(0)

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the todo items."""
        child_data = self._get_child_data()
        if not child_data:
            return None
        tasks = child_data.get("tasks", {})

        # Use a dict to deduplicate tasks by their unique ID
        unique_tasks = {}

        # Add tasks from all categories, but deduplicate by task ID
        all_task_lists = [
            tasks.get("upcoming", []),
            tasks.get("overdue", []),
            tasks.get("due_today", []),
        ]

        for task_list in all_task_lists:
            for task in task_list:
                task_id = task.get("id")
                if task_id and task_id not in unique_tasks:
                    status = self._map_completion_status(task.get("completionStatus", "Todo"))
                    unique_tasks[task_id] = self._create_todo_item(task, status)

        return list(unique_tasks.values())

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
        if task_data.get("setter"):
            description_parts.append(f"Set by: {task_data['setter']}")
        if task_data.get("task_type"):
            description_parts.append(f"Type: {task_data['task_type']}")
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
