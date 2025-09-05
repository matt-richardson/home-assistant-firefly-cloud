"""Test the Firefly Cloud todo platform."""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, Mock

from homeassistant.components.todo import TodoItem, TodoItemStatus
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.firefly_cloud.const import DOMAIN, CONF_SCHOOL_NAME, CONF_USER_GUID
from custom_components.firefly_cloud.todo import FireflyTodoListEntity
from custom_components.firefly_cloud.coordinator import FireflyUpdateCoordinator


@pytest.fixture
def mock_coordinator():
    """Create a mock coordinator."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    coordinator.last_update_success = True

    # Mock data structure matching the coordinator
    mock_task = {
        "id": "task123",
        "title": "Math Homework",
        "subject": "Mathematics",
        "due_date": datetime.now(timezone.utc),
        "task_type": "homework",
        "setter": "Mr. Smith",
        "description": "Complete exercises 1-10",
    }

    coordinator.data = {
        "children_data": {
            "child123": {
                "name": "Test Child",
                "tasks": {
                    "upcoming": [mock_task],
                    "due_today": [mock_task],
                    "overdue": [],
                },
            }
        }
    }

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
        assert "Test School Tasks" in todo_entity._base_name
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
        assert "Test School Tasks" in name

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
        mock_coordinator.data = {"children_data": {}}
        assert todo_entity.available is False

    def test_todo_items(self, todo_entity):
        """Test todo items property."""
        items = todo_entity.todo_items
        assert len(items) == 2  # upcoming + due_today (same task appears twice)

        # Test first item
        item = items[0]
        assert isinstance(item, TodoItem)
        assert item.summary == "Math Homework"
        assert item.status == TodoItemStatus.NEEDS_ACTION
        assert item.due is not None
        assert "Type: homework" in item.description
        assert "Set by: Mr. Smith" in item.description
        assert "Complete exercises 1-10" in item.description

    def test_todo_items_without_data(self, todo_entity, mock_coordinator):
        """Test todo items with no data."""
        mock_coordinator.data = None
        assert todo_entity.todo_items is None

    def test_todo_items_without_child(self, todo_entity, mock_coordinator):
        """Test todo items without child data."""
        mock_coordinator.data = {"children_data": {}}
        assert todo_entity.todo_items is None

    def test_create_todo_item_from_task_data(self, todo_entity):
        """Test creating todo item from task data."""
        task_data = {
            "id": "test123",
            "title": "Science Project",
            "subject": "Science",
            "due_date": datetime(2023, 12, 25, 9, 0, 0, tzinfo=timezone.utc),
            "task_type": "project",
            "setter": "Ms. Johnson",
            "description": "Build a volcano model",
        }

        item = todo_entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)

        assert item.summary == "Science Project"
        assert item.status == TodoItemStatus.NEEDS_ACTION
        assert item.due == datetime(2023, 12, 25, 9, 0, 0, tzinfo=timezone.utc)
        assert "Type: project" in item.description
        assert "Set by: Ms. Johnson" in item.description
        assert "Build a volcano model" in item.description
        assert len(item.uid) <= 50  # Ensure UID is within limits

    def test_create_todo_item_minimal_data(self, todo_entity):
        """Test creating todo item with minimal data."""
        task_data = {
            "title": "Basic Task",
        }

        item = todo_entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)

        assert item.summary == "Basic Task"
        assert item.status == TodoItemStatus.NEEDS_ACTION
        assert item.due is None
        assert item.description is None

    @pytest.mark.asyncio
    async def test_read_only_operations(self, todo_entity):
        """Test that all modification operations raise NotImplementedError."""
        test_item = TodoItem(uid="test", summary="Test Task", status=TodoItemStatus.NEEDS_ACTION)

        with pytest.raises(NotImplementedError, match="read-only"):
            await todo_entity.async_create_todo_item(test_item)

        with pytest.raises(NotImplementedError, match="read-only"):
            await todo_entity.async_delete_todo_items(["test"])

        with pytest.raises(NotImplementedError, match="read-only"):
            await todo_entity.async_update_todo_item(test_item)

        with pytest.raises(NotImplementedError, match="read-only"):
            await todo_entity.async_move_todo_item("test", "prev")


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

    async_add_entities = AsyncMock()

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
    
    task_data = {
        "title": "Task Without Due Date",
        "description": "No due date",
        "subject": {"name": "Math"},
        "completionStatus": "Todo",
        # Missing dueDate
    }
    
    todo_item = entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)
    
    assert todo_item.summary == "Task Without Due Date"
    assert todo_item.due is None  # Should handle missing due date gracefully


@pytest.mark.asyncio  
async def test_create_todo_item_with_invalid_due_date():
    """Test create_todo_item with invalid due date format."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    config_entry = Mock(spec=ConfigEntry)
    config_entry.data = {"school_name": "Test School"}
    config_entry.entry_id = "test-entry"
    
    entity = FireflyTodoListEntity(coordinator, config_entry, "test-child-123")
    
    task_data = {
        "title": "Task With Bad Date",
        "description": "Invalid date format",
        "dueDate": "not-a-valid-date",
        "subject": {"name": "Science"},
        "completionStatus": "Todo",
    }
    
    todo_item = entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)
    
    assert todo_item.summary == "Task With Bad Date"
    assert todo_item.due is None  # Should handle invalid date gracefully


@pytest.mark.asyncio
async def test_create_todo_item_with_missing_subject():
    """Test create_todo_item with missing subject."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    config_entry = Mock(spec=ConfigEntry)
    config_entry.data = {"school_name": "Test School"}
    config_entry.entry_id = "test-entry"
    
    entity = FireflyTodoListEntity(coordinator, config_entry, "test-child-123")
    
    task_data = {
        "title": "Task Without Subject",
        "description": "No subject field",
        "dueDate": "2023-12-31T23:59:59Z",
        "completionStatus": "Todo",
        # Missing subject field
    }
    
    todo_item = entity._create_todo_item(task_data, TodoItemStatus.NEEDS_ACTION)
    
    assert todo_item.summary == "Task Without Subject"
    # Should handle missing subject gracefully
    assert "No subject field" in todo_item.description


@pytest.mark.asyncio
async def test_todo_items_with_mixed_completion_status():
    """Test todo_items with mixed completion status."""
    coordinator = Mock(spec=FireflyUpdateCoordinator)
    coordinator.data = {
        "children_data": {
            "test-child-123": {
                "name": "Test Child",
                "tasks": {
                    "upcoming": [
                        {
                            "title": "Completed Task",
                            "description": "This is done",
                            "dueDate": "2023-12-31T23:59:59Z",
                            "subject": {"name": "Math"},
                            "completionStatus": "Done",  # Completed
                        },
                        {
                            "title": "Pending Task", 
                            "description": "Still to do",
                            "dueDate": "2023-12-25T12:00:00Z",
                            "subject": {"name": "English"},
                            "completionStatus": "Todo",  # Not completed
                        }
                    ],
                    "overdue": [],
                    "due_today": []
                }
            }
        }
    }
    
    config_entry = Mock(spec=ConfigEntry)
    config_entry.data = {"school_name": "Test School"}
    config_entry.entry_id = "test-entry"
    entity = FireflyTodoListEntity(coordinator, config_entry, "test-child-123")
    
    todo_items = entity.todo_items
    
    # Should include both completed and pending tasks
    assert len(todo_items) == 2
    
    # Check that completed status is properly mapped
    completed_item = next(item for item in todo_items if item.summary == "Completed Task")
    pending_item = next(item for item in todo_items if item.summary == "Pending Task")
    
    assert completed_item.status == TodoItemStatus.COMPLETED
    assert pending_item.status == TodoItemStatus.NEEDS_ACTION
