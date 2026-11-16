"""Test the Firefly Cloud todo platform."""

from datetime import date, datetime
from unittest.mock import Mock

import pytest
from conftest import make_child, make_data, make_task
from homeassistant.components.todo import TodoItem, TodoItemStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.firefly_cloud.const import CONF_SCHOOL_NAME, CONF_USER_GUID, DOMAIN
from custom_components.firefly_cloud.coordinator import FireflyUpdateCoordinator
from custom_components.firefly_cloud.todo import FireflyTodoListEntity

TODAY = date(2026, 11, 16)


def _data(*tasks, guid="test-child-123"):
    """Build coordinator data holding one child with these tasks."""
    return make_data(make_child(guid, tasks=tasks, today=TODAY))


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    coordinator.last_update_success = True

    mock_task = make_task(
        "task123",
        title="Math Homework",
        subject="Mathematics",
        due=TODAY,
        setter="Mr. Smith",
        description="Complete exercises 1-10",
    )
    coordinator.data = make_data(make_child("child123", tasks=[mock_task], today=TODAY, name="Test Child"))

    return coordinator


@pytest.fixture
def mock_config_entry():
    """Create a mock config entry."""
    config_entry = Mock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry"
    config_entry.data = {
        CONF_SCHOOL_NAME: "Test School",
        CONF_USER_GUID: "user123",
        "host": "https://test.fireflysolutions.co.uk",
    }
    return config_entry


@pytest.fixture
def todo_entity(mock_coordinator, mock_config_entry):
    """Create a todo entity for testing."""
    return FireflyTodoListEntity(
        coordinator=mock_coordinator,
        config_entry=mock_config_entry,
        child_guid="child123",
    )


class TestFireflyTodoListEntity:
    """Test the Firefly todo list entity."""

    def test_init(self, todo_entity, mock_config_entry):
        """Test entity initialization."""
        assert todo_entity._child_guid == "child123"
        assert todo_entity._config_entry == mock_config_entry
        assert todo_entity.unique_id == "test_entry_todo_child123"
        assert "Tasks" == todo_entity._base_name
        assert todo_entity.icon == "mdi:clipboard-check"

        # Test device info
        device_info = todo_entity.device_info
        assert device_info["name"] == "Firefly Cloud - Test School"
        assert device_info["manufacturer"] == "Firefly Learning"

        # Test supported features (read-only)
        assert todo_entity.supported_features == 0

    def test_name_with_child_data(self, todo_entity):
        """Test entity name with child data available."""
        name = todo_entity.name
        assert "Test Child" in name
        assert name == "Tasks (Test Child)"

    def test_name_without_child_data(self, todo_entity, mock_coordinator):
        """Test entity name without child data."""
        mock_coordinator.data = None
        name = todo_entity.name
        assert "child123"[:8] in name  # Uses GUID prefix

    def test_available_with_data(self, todo_entity):
        """Test entity availability with data."""
        assert todo_entity.available is True

    def test_available_without_data(self, todo_entity, mock_coordinator):
        """Test entity availability without data."""
        mock_coordinator.last_update_success = False
        assert todo_entity.available is False

    def test_available_without_child(self, todo_entity, mock_coordinator):
        """Test entity availability without child data."""
        mock_coordinator.data = make_data()
        assert todo_entity.available is False

    def test_todo_items(self, todo_entity):
        """Test todo items property."""
        items = todo_entity.todo_items
        assert len(items) == 1  # Same task in upcoming + due_today should be deduplicated

        # Test first item
        item = items[0]
        assert isinstance(item, TodoItem)
        assert item.summary == "Math Homework"
        assert item.status == TodoItemStatus.NEEDS_ACTION
        assert item.due is not None
        assert item.description is not None
        assert "Set by: Mr. Smith" in item.description
        assert "Complete exercises 1-10" in item.description

    def test_todo_items_without_data(self, todo_entity, mock_coordinator):
        """Test todo items with no data."""
        mock_coordinator.data = None
        assert todo_entity.todo_items is None

    def test_todo_items_without_child(self, todo_entity, mock_coordinator):
        """Test todo items without child data."""
        mock_coordinator.data = make_data()
        assert todo_entity.todo_items is None

    def test_create_todo_item_from_task_data(self, todo_entity):
        """Test creating todo item from task data."""
        task_data = make_task(
            "test123",
            title="Science Project",
            subject="Science",
            due=date(2023, 12, 25),
            setter="Ms. Johnson",
            description="Build a volcano model",
        )

        item = todo_entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)

        assert item.summary == "Science Project"
        assert item.status == TodoItemStatus.NEEDS_ACTION
        assert item.due == date(2023, 12, 25)
        assert "Set by: Ms. Johnson" in item.description
        assert "Build a volcano model" in item.description
        assert len(item.uid) <= 50  # Ensure UID is within limits

    def test_todo_due_is_date(self, todo_entity):
        """The todo due is the calendar date, with no time."""
        task_data = make_task("1", title="T", due=date(2026, 11, 20))

        item = todo_entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)

        assert item.due == date(2026, 11, 20)
        assert not isinstance(item.due, datetime)

    def test_create_todo_item_minimal_data(self, todo_entity):
        """Test creating todo item with minimal data."""
        task_data = make_task("", title="Basic Task", setter=None)

        item = todo_entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)

        assert item.summary == "Basic Task"
        assert item.status == TodoItemStatus.NEEDS_ACTION
        assert item.due is None
        assert item.description is None


@pytest.mark.asyncio
async def test_async_setup_entry():
    """Test the async_setup_entry function."""
    from custom_components.firefly_cloud.todo import async_setup_entry

    hass = Mock(spec=HomeAssistant)
    config_entry = Mock(spec=ConfigEntry)
    config_entry.entry_id = "test_entry"
    config_entry.data = {
        CONF_SCHOOL_NAME: "Test School",
        CONF_USER_GUID: "user123",
    }

    coordinator = Mock(spec=FireflyUpdateCoordinator)
    hass.data = {DOMAIN: {"test_entry": coordinator}}

    async_add_entities = Mock()

    await async_setup_entry(hass, config_entry, async_add_entities)

    # Verify entity was created and added
    async_add_entities.assert_called_once()
    entities = async_add_entities.call_args[0][0]
    assert len(entities) == 1
    assert isinstance(entities[0], FireflyTodoListEntity)


@pytest.mark.asyncio
async def test_create_todo_item_with_missing_due_date():
    """Test create_todo_item with missing due date."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    config_entry = Mock(spec=ConfigEntry)
    config_entry.data = {"school_name": "Test School"}
    config_entry.entry_id = "test-entry"

    entity = FireflyTodoListEntity(coordinator, config_entry, "test-child-123")

    task_data = make_task("t1", title="Task Without Due Date", description="No due date", due=None)

    todo_item = entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)

    assert todo_item.summary == "Task Without Due Date"
    assert todo_item.due is None  # Should handle missing due date gracefully


@pytest.mark.asyncio
async def test_create_todo_item_with_missing_subject():
    """Test create_todo_item with missing subject."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    config_entry = Mock(spec=ConfigEntry)
    config_entry.data = {"school_name": "Test School"}
    config_entry.entry_id = "test-entry"

    entity = FireflyTodoListEntity(coordinator, config_entry, "test-child-123")

    task_data = make_task(
        "t1",
        title="Task Without Subject",
        description="No subject field",
        subject=None,
        due=date(2023, 12, 31),
    )

    todo_item = entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)

    assert todo_item.summary == "Task Without Subject"
    # Should handle missing subject gracefully
    assert todo_item.description is not None
    assert "No subject field" in todo_item.description


@pytest.mark.asyncio
async def test_todo_items_with_mixed_completion_status():
    """Test todo_items with mixed completion status."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    coordinator.data = _data(
        make_task(
            "completed123",
            title="Completed Task",
            description="This is done",
            subject="Math",
            due=TODAY,
            completion_status="Completed",
        ),
        make_task(
            "pending456",
            title="Pending Task",
            description="Still to do",
            subject="English",
            due=TODAY,
            completion_status="Todo",
        ),
    )

    config_entry = Mock(spec=ConfigEntry)
    config_entry.data = {"school_name": "Test School"}
    config_entry.entry_id = "test-entry"
    entity = FireflyTodoListEntity(coordinator, config_entry, "test-child-123")

    todo_items = entity.todo_items

    # Should include both completed and pending tasks
    assert todo_items is not None
    assert len(todo_items) == 2

    # Check that completed status is properly mapped
    completed_item = next(item for item in todo_items if item.summary == "Completed Task")
    pending_item = next(item for item in todo_items if item.summary == "Pending Task")

    assert completed_item.status == TodoItemStatus.COMPLETED
    assert pending_item.status == TodoItemStatus.NEEDS_ACTION


@pytest.mark.asyncio
async def test_todo_items_deduplication():
    """Test that duplicate tasks across categories are properly deduplicated."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    coordinator.last_update_success = True

    # A task due today is both upcoming and due today
    duplicate_task = make_task(
        "duplicate123",
        title="Same Task",
        description="Appears in multiple lists",
        due=TODAY,
        setter="Teacher",
    )

    # Different task to ensure we're not losing other tasks
    unique_task = make_task(
        "unique456",
        title="Different Task",
        description="Only appears once",
        due=date(2026, 11, 18),
        setter="Teacher2",
    )

    coordinator.data = _data(duplicate_task, unique_task)

    config_entry = Mock(spec=ConfigEntry)
    config_entry.data = {CONF_SCHOOL_NAME: "Test School"}
    config_entry.entry_id = "test-entry"

    entity = FireflyTodoListEntity(coordinator, config_entry, "test-child-123")
    todo_items = entity.todo_items

    # Should only have 2 unique tasks, despite duplicate_task appearing 3 times
    assert todo_items is not None
    assert len(todo_items) == 2

    # Verify we have the correct unique tasks
    task_titles = {item.summary for item in todo_items}
    assert "Same Task" in task_titles
    assert "Different Task" in task_titles


@pytest.mark.asyncio
async def test_todo_items_with_tasks_missing_ids():
    """Test handling of tasks that don't have IDs (should be skipped)."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    coordinator.last_update_success = True

    # Task without ID should be skipped during deduplication
    task_without_id = make_task("", title="No ID Task", description="Missing ID field", due=TODAY)

    # Task with ID should be included
    task_with_id = make_task("valid123", title="Valid Task", description="Has proper ID", due=TODAY)

    coordinator.data = _data(task_without_id, task_with_id)

    config_entry = Mock(spec=ConfigEntry)
    config_entry.data = {CONF_SCHOOL_NAME: "Test School"}
    config_entry.entry_id = "test-entry"

    entity = FireflyTodoListEntity(coordinator, config_entry, "test-child-123")
    todo_items = entity.todo_items

    # Should only include task with valid ID
    assert todo_items is not None
    assert len(todo_items) == 1
    assert todo_items[0].summary == "Valid Task"
