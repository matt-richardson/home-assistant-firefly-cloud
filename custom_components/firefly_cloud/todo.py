"""Todo platform for Firefly Cloud integration."""

from typing import List

from homeassistant.components.todo import TodoItem, TodoListEntity
from homeassistant.components.todo.const import TodoItemStatus, TodoListEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import FireflyUpdateCoordinator
from .entity import FireflyBaseEntity
from .entry_config import child_guids
from .models import Task


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
        child = self._child
        if child is None:
            return None

        # Use a dict to deduplicate tasks by their unique ID
        unique_tasks: dict[str, TodoItem] = {}

        # Add tasks from all categories, but deduplicate by task ID
        for task_list in (child.upcoming, child.overdue, child.due_today):
            for task in task_list:
                if task.id and task.id not in unique_tasks:
                    status = TodoItemStatus.COMPLETED if task.is_completed else TodoItemStatus.NEEDS_ACTION
                    unique_tasks[task.id] = self._create_todo_item(task, status)

        return list(unique_tasks.values())

    def _create_todo_item(self, task: Task, status: TodoItemStatus) -> TodoItem:
        """Create a TodoItem from a task."""
        # Create unique ID from task data
        uid = f"{task.id}_{task.title}"
        uid = uid.replace(" ", "_").replace("/", "_")[:50]  # Limit length and sanitize

        # Create description with additional details
        description_parts = []
        if task.setter:
            description_parts.append(f"Set by: {task.setter}")
        if task.description:
            description_parts.append(task.description)

        description = "\n".join(description_parts) if description_parts else None

        return TodoItem(
            uid=uid,
            summary=task.title,
            status=status,
            due=task.due,
            description=description,
        )
