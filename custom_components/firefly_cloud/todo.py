"""Todo platform for Firefly Cloud integration."""

from datetime import date, datetime
from typing import Any, Dict, List

from homeassistant.components.todo import TodoItem, TodoListEntity
from homeassistant.components.todo.const import TodoItemStatus, TodoListEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TASK_STATUS_COMPLETED
from .coordinator import FireflyUpdateCoordinator
from .entity import FireflyBaseEntity
from .entry_config import child_guids


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Firefly Cloud todo platform."""
    coordinator: FireflyUpdateCoordinator = hass.data[DOMAIN][config_entry.entry_id]

    # Create todo list for each child
    entities: List[TodoListEntity] = []

    for child_guid in child_guids(config_entry):
        entities.append(
            FireflyTodoListEntity(
                coordinator=coordinator,
                config_entry=config_entry,
                child_guid=child_guid,
            )
        )

    async_add_entities(entities)


class FireflyTodoListEntity(FireflyBaseEntity, TodoListEntity):  # pylint: disable=abstract-method  # read-only
    """Firefly todo list entity."""

    def __init__(
        self,
        coordinator: FireflyUpdateCoordinator,
        config_entry: ConfigEntry,
        child_guid: str,
    ) -> None:
        """Initialize the todo list entity."""
        base_name = "Tasks"

        super().__init__(coordinator, config_entry, child_guid, base_name)

        self._config_entry = config_entry

        # Generate unique entity ID
        self._attr_unique_id = f"{config_entry.entry_id}_todo_{child_guid}"

        # Set entity properties
        self._attr_icon = "mdi:clipboard-check"

        # Firefly is read-only, so no creating, editing or deleting items
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
                    status = self._map_completion_status(task.get("completion_status"))
                    unique_tasks[task_id] = self._create_todo_item(task, status)

        return list(unique_tasks.values())

    def _map_completion_status(self, completion_status: str | None) -> TodoItemStatus:
        """Map a processed task's Firefly completion status to TodoItemStatus."""
        if (completion_status or "").lower() == TASK_STATUS_COMPLETED.lower():
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

        # Due dates are calendar dates (local midnight), so report a date with no time
        due = None
        if task_data.get("due_date"):
            due_date = task_data["due_date"]
            if isinstance(due_date, datetime):
                due = due_date.date()
            elif isinstance(due_date, date):
                due = due_date

        # Create description with additional details
        description_parts = []
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
