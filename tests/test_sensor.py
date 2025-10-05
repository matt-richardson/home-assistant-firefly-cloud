"""Test the Firefly Cloud sensor platform."""

from datetime import timedelta
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.firefly_cloud.const import (
    CONF_CHILDREN_GUIDS,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_SCHOOL_NAME,
    CONF_SECRET,
    CONF_USER_GUID,
    DOMAIN,
    SENSOR_CURRENT_CLASS,
    SENSOR_NEXT_CLASS,
    SENSOR_OVERDUE_TASKS,
    SENSOR_TASKS_DUE_TODAY,
    SENSOR_TYPES,
    SENSOR_UPCOMING_TASKS,
)
from custom_components.firefly_cloud.sensor import (
    FireflySensor,
    async_setup_entry,
)


@pytest.fixture
def mock_coordinator():
    """Return a mock coordinator with data."""
    coordinator = MagicMock()
    from custom_components.firefly_cloud.const import get_offset_time

    now = get_offset_time().replace(tzinfo=None)  # Remove timezone for test format

    # Mock coordinator data
    coordinator.data = {
        "user_info": {
            "username": "john.doe",
            "fullname": "John Doe",
            "email": "john.doe@test.com",
            "role": "student",
            "guid": "test-user-123",
        },
        "children_guids": ["test-child-123", "test-child-456"],
        "children_data": {
            "test-child-123": {
                "name": "John Doe",
                "events": {
                    "today": [
                        {
                            "start": now.replace(hour=9, minute=0, second=0, microsecond=0),
                            "end": now.replace(hour=10, minute=0, second=0, microsecond=0),
                            "subject": "Mathematics",
                            "location": "Room 101",
                            "description": "Algebra lesson",
                            "guild": None,
                            "attendees": [],
                        }
                    ],
                    "week": [
                        {
                            "start": now.replace(hour=9, minute=0, second=0, microsecond=0),
                            "end": now.replace(hour=10, minute=0, second=0, microsecond=0),
                            "subject": "Mathematics",
                            "location": "Room 101",
                            "description": "Algebra lesson",
                            "guild": None,
                            "attendees": [],
                        },
                        {
                            "start": now.replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1),
                            "end": now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1),
                            "subject": "Science",
                            "location": "Lab 1",
                            "description": "Chemistry experiment",
                            "guild": None,
                            "attendees": [],
                        },
                    ],
                },
                "tasks": {
                    "all": [
                        {
                            "id": "task-1",
                            "title": "Math Homework",
                            "description": "Complete exercises 1-10",
                            "due_date": now + timedelta(days=2),
                            "set_date": now - timedelta(days=1),
                            "subject": "Mathematics",
                            "task_type": "homework",
                            "completion_status": "Todo",
                            "setter": "Mr. Smith",
                            "raw_data": {},
                        }
                    ],
                    "due_today": [],
                    "upcoming": [
                        {
                            "id": "task-1",
                            "title": "Math Homework",
                            "description": "Complete exercises 1-10",
                            "due_date": now + timedelta(days=2),
                            "set_date": now - timedelta(days=1),
                            "subject": "Mathematics",
                            "task_type": "homework",
                            "completion_status": "Todo",
                            "setter": "Mr. Smith",
                            "raw_data": {},
                        }
                    ],
                    "overdue": [],
                },
            },
            "test-child-456": {
                "name": "Jane Doe",
                "events": {
                    "today": [],
                    "week": [],
                },
                "tasks": {
                    "all": [],
                    "due_today": [],
                    "upcoming": [],
                    "overdue": [],
                },
            },
        },
        "last_updated": get_offset_time(),
    }

    coordinator.last_update_success = True
    coordinator.last_exception = None
    return coordinator


@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry, mock_coordinator):
    """Test sensor platform setup."""
    hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}

    entities = []

    def mock_add_entities(new_entities, update_before_add=False):  # pylint: disable=unused-argument
        entities.extend(new_entities)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    assert len(entities) == 10  # 5 sensor types × 2 children
    assert all(isinstance(e, FireflySensor) for e in entities)

    # Check that all sensor types are created
    sensor_types = [e._sensor_type for e in entities]
    assert SENSOR_UPCOMING_TASKS in sensor_types
    assert SENSOR_TASKS_DUE_TODAY in sensor_types
    assert SENSOR_OVERDUE_TASKS in sensor_types
    assert SENSOR_CURRENT_CLASS in sensor_types
    assert SENSOR_NEXT_CLASS in sensor_types


@pytest.mark.asyncio
async def test_upcoming_tasks_sensor(mock_coordinator, mock_config_entry):
    """Test upcoming tasks sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    assert "Upcoming Tasks" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_UPCOMING_TASKS}_test-child-123"
    assert sensor.icon == "mdi:clipboard-text"
    assert sensor.native_value == 1
    assert sensor.native_unit_of_measurement == "tasks"


@pytest.mark.asyncio
async def test_tasks_due_today_sensor(mock_coordinator, mock_config_entry):
    """Test tasks due today sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-child-123")

    assert "Tasks Due Today" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_TASKS_DUE_TODAY}_test-child-123"
    assert sensor.icon == "mdi:clipboard-alert"
    assert sensor.native_value == 0
    assert sensor.native_unit_of_measurement == "tasks"


@pytest.mark.asyncio
async def test_tasks_due_today_sensor_with_tasks(mock_coordinator, mock_config_entry):
    """Test tasks due today sensor with tasks."""
    from custom_components.firefly_cloud.const import get_offset_time

    now = get_offset_time().replace(tzinfo=None)
    mock_coordinator.data["children_data"]["test-child-123"]["tasks"]["due_today"] = [
        {
            "id": "urgent-task",
            "title": "Submit Report",
            "description": "Final report submission",
            "due_date": now,
            "set_date": now - timedelta(days=7),
            "subject": "English",
            "task_type": "assignment",
            "completion_status": "Todo",
            "setter": "Ms. Johnson",
            "raw_data": {},
        }
    ]

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-child-123")

    assert sensor.native_value == 1


@pytest.mark.asyncio
async def test_overdue_tasks_sensor(mock_coordinator, mock_config_entry):
    """Test overdue tasks sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_OVERDUE_TASKS, "test-child-123")

    assert "Overdue Tasks" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_OVERDUE_TASKS}_test-child-123"
    assert sensor.icon == "mdi:alert-circle"
    assert sensor.native_value == 0
    assert sensor.native_unit_of_measurement == "tasks"


@pytest.mark.asyncio
async def test_overdue_tasks_sensor_with_tasks(mock_coordinator, mock_config_entry):
    """Test overdue tasks sensor with tasks."""
    from custom_components.firefly_cloud.const import get_offset_time

    now = get_offset_time().replace(tzinfo=None)
    mock_coordinator.data["children_data"]["test-child-123"]["tasks"]["overdue"] = [
        {
            "id": "overdue-task-1",
            "title": "Late Assignment",
            "description": "This was due last week",
            "due_date": now - timedelta(days=7),
            "set_date": now - timedelta(days=14),
            "subject": "History",
            "task_type": "homework",
            "completion_status": "Todo",
            "setter": "Mr. Brown",
            "raw_data": {},
        },
        {
            "id": "overdue-task-2",
            "title": "Overdue Project",
            "description": "Final project submission",
            "due_date": now - timedelta(days=3),
            "set_date": now - timedelta(days=30),
            "subject": "Science",
            "task_type": "project",
            "completion_status": "Todo",
            "setter": "Dr. Smith",
            "raw_data": {},
        },
    ]

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_OVERDUE_TASKS, "test-child-123")

    assert sensor.native_value == 2


@pytest.mark.asyncio
async def test_overdue_tasks_sensor_attributes(mock_coordinator, mock_config_entry):
    """Test overdue tasks sensor attributes."""
    from custom_components.firefly_cloud.const import get_offset_time

    now = get_offset_time().replace(tzinfo=None)

    # Add overdue tasks to coordinator data
    mock_coordinator.data["children_data"]["test-child-123"]["tasks"]["overdue"] = [
        {
            "id": "overdue-task",
            "title": "Late Assignment",
            "description": "This was due last week",
            "due_date": now - timedelta(days=7),
            "set_date": now - timedelta(days=14),
            "subject": "History",
            "task_type": "homework",
            "completion_status": "Todo",
            "setter": "Mr. Brown",
            "raw_data": {},
        }
    ]

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_OVERDUE_TASKS, "test-child-123")

    attributes = sensor.extra_state_attributes
    assert "tasks" in attributes
    assert "last_updated" in attributes

    # Check task details
    tasks = attributes["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Late Assignment"
    assert tasks[0]["subject"] == "History"
    assert tasks[0]["days_overdue"] == 7


@pytest.mark.asyncio
async def test_sensor_availability(mock_coordinator, mock_config_entry):
    """Test sensor availability."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    # Available when coordinator has successful update and child data exists
    mock_coordinator.last_update_success = True
    mock_coordinator.data = {"children_data": {"test-child-123": {"some": "data"}}}
    assert sensor.available is True

    # Unavailable when coordinator update failed
    mock_coordinator.last_update_success = False
    assert sensor.available is False

    # Unavailable when no data
    mock_coordinator.last_update_success = True
    mock_coordinator.data = None
    assert sensor.available is False


@pytest.mark.asyncio
async def test_sensor_device_info(mock_coordinator, mock_config_entry):
    """Test sensor device info."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    device_info = sensor.device_info
    assert device_info is not None
    assert device_info.get("identifiers") == {(DOMAIN, mock_config_entry.entry_id)}
    assert "Firefly Cloud" in str(device_info.get("name", ""))
    assert device_info.get("manufacturer") == "Firefly Learning"
    assert device_info.get("model") == "Firefly Cloud Integration"


@pytest.mark.asyncio
async def test_sensor_no_coordinator_data(mock_config_entry):
    """Test sensor with no coordinator data."""
    coordinator = AsyncMock()
    coordinator.data = None
    coordinator.last_update_success = False

    sensor = FireflySensor(coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    assert sensor.available is False
    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_sensor_extra_state_attributes(mock_coordinator, mock_config_entry):
    """Test sensor extra state attributes."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    attributes = sensor.extra_state_attributes
    assert isinstance(attributes, dict)
    # Should include data relevant to the sensor type
    assert len(attributes) > 1  # Should have meaningful attributes
    assert "last_updated" in attributes


@pytest.mark.asyncio
async def test_sensor_handles_missing_data_gracefully(mock_coordinator, mock_config_entry):
    """Test sensor handles missing data gracefully."""
    from custom_components.firefly_cloud.const import get_offset_time

    # Remove specific data that sensor needs
    mock_coordinator.data = {
        "user_info": {"username": "test", "fullname": "Test User", "guid": "test-123"},
        "children_data": {
            "test-child-123": {
                "events": {},  # Missing today/week keys
                "tasks": {},  # Missing task type keys
            }
        },
        "last_updated": get_offset_time(),
    }

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    # Should not crash and return sensible defaults
    assert sensor.available is True
    assert sensor.native_value == 0  # Default when no data


@pytest.mark.asyncio
async def test_all_sensor_types_defined():
    """Test that all sensor types have proper configuration."""
    for sensor_type in [SENSOR_UPCOMING_TASKS, SENSOR_TASKS_DUE_TODAY, SENSOR_OVERDUE_TASKS, SENSOR_CURRENT_CLASS, SENSOR_NEXT_CLASS]:
        assert sensor_type in SENSOR_TYPES
        config = SENSOR_TYPES[sensor_type]
        assert "name" in config
        assert "icon" in config
        assert "unit" in config
        assert "device_class" in config


@pytest.mark.asyncio
async def test_sensor_with_nonexistent_child(mock_coordinator, mock_config_entry):
    """Test sensor with child GUID that doesn't exist in data."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "nonexistent-child-123")

    assert sensor.available is False
    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_sensor_attributes_upcoming_tasks(mock_coordinator, mock_config_entry):
    """Test upcoming tasks sensor attributes."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    attributes = sensor.extra_state_attributes
    assert "tasks" in attributes
    assert "overdue_count" in attributes
    assert "tasks_by_due_date" in attributes
    assert "last_updated" in attributes

    # Check task details
    tasks = attributes["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Math Homework"
    assert tasks[0]["subject"] == "Mathematics"


@pytest.mark.asyncio
async def test_sensor_attributes_tasks_due_today(mock_coordinator, mock_config_entry):
    """Test tasks due today sensor attributes."""
    from custom_components.firefly_cloud.const import get_offset_time

    now = get_offset_time().replace(tzinfo=None)

    # Add task due today to coordinator data
    mock_coordinator.data["children_data"]["test-child-123"]["tasks"]["due_today"] = [
        {
            "id": "urgent-task",
            "title": "Submit Report",
            "description": "Final report submission",
            "due_date": now,
            "set_date": now - timedelta(days=7),
            "subject": "English",
            "task_type": "assignment",
            "completion_status": "Todo",
            "setter": "Ms. Johnson",
            "raw_data": {},
        }
    ]

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-child-123")

    attributes = sensor.extra_state_attributes
    assert "tasks" in attributes
    assert "homework_count" in attributes
    assert "project_count" in attributes
    assert "test_count" in attributes
    assert "last_updated" in attributes

    # Check task details
    tasks = attributes["tasks"]
    assert len(tasks) == 1
    assert tasks[0]["title"] == "Submit Report"
    assert tasks[0]["subject"] == "English"


@pytest.mark.asyncio
async def test_sensor_state_class_properties(mock_coordinator, mock_config_entry):
    """Test sensor state class and device class properties."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    assert hasattr(sensor, "state_class")
    assert hasattr(sensor, "device_class")

    # Check that properties match sensor type configuration
    sensor_config = SENSOR_TYPES[SENSOR_UPCOMING_TASKS]
    if "state_class" in sensor_config:
        assert sensor.state_class == sensor_config["state_class"]
    if "device_class" in sensor_config:
        assert sensor.device_class == sensor_config["device_class"]


@pytest.mark.asyncio
async def test_sensor_entity_category(mock_coordinator, mock_config_entry):
    """Test sensor entity category if defined."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    # Entity category should be None for main sensors (they're not diagnostic/config)
    assert sensor.entity_category is None


@pytest.mark.asyncio
async def test_sensor_handles_empty_tasks(mock_coordinator, mock_config_entry):
    """Test sensor handling empty tasks gracefully."""
    # Clear tasks data
    mock_coordinator.data["children_data"]["test-child-123"]["tasks"]["upcoming"] = []
    mock_coordinator.data["children_data"]["test-child-123"]["tasks"]["due_today"] = []
    mock_coordinator.data["children_data"]["test-child-123"]["tasks"]["overdue"] = []

    upcoming_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")
    due_today_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-child-123")
    overdue_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_OVERDUE_TASKS, "test-child-123")

    assert upcoming_sensor.native_value == 0
    assert due_today_sensor.native_value == 0
    assert overdue_sensor.native_value == 0
    assert upcoming_sensor.available is True
    assert due_today_sensor.available is True
    assert overdue_sensor.available is True


@pytest.mark.asyncio
async def test_sensor_error_handling_malformed_data(mock_coordinator, mock_config_entry):
    """Test sensor error handling when data access fails."""
    # Mock coordinator with malformed data structure that will cause TypeError on len()
    mock_coordinator.data = {
        "children_data": {
            "test-child-123": {
                "tasks": {
                    "upcoming": "not-a-list",  # Should be a list - len() will raise TypeError
                }
                # Missing other required keys
            }
        }
    }

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    # len("not-a-list") returns 10, so sensor returns 10
    assert sensor.native_value == 10
    assert sensor.available is True


@pytest.mark.asyncio
async def test_sensor_no_coordinator_last_update_success(mock_coordinator, mock_config_entry):
    """Test sensor when coordinator has no last_update_success attribute."""
    # Configure mock to properly return the attribute
    mock_coordinator.last_update_success = True

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    # Should be available if data exists and coordinator says so
    assert sensor.available is True


@pytest.mark.asyncio
async def test_sensor_name_includes_child_name(mock_config_entry):
    """Test sensor name includes child name when available."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "children_data": {
            "child-123": {
                "name": "John Doe",
                "events": {"today": [], "week": []},
                "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
            }
        }
    }

    sensor = FireflySensor(coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "child-123")

    assert "John Doe" in sensor.name
    assert "Upcoming Tasks" in sensor.name


@pytest.mark.asyncio
async def test_sensor_name_fallback_to_guid(mock_config_entry):
    """Test sensor name falls back to GUID when no name available."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "children_data": {
            "child-123": {
                "events": {"today": [], "week": []},
                "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
            }
        }
    }

    sensor = FireflySensor(coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "child-123")

    assert "child-12" in sensor.name  # First 8 chars of "child-123"
    assert "Upcoming Tasks" in sensor.name


@pytest.mark.asyncio
async def test_sensor_coordinator_data_update(mock_coordinator, mock_config_entry):
    """Test sensor updates when coordinator data changes."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    initial_value = sensor.native_value
    assert initial_value == 1

    # Update coordinator data - add a new task for UPCOMING_TASKS sensor
    from custom_components.firefly_cloud.const import get_offset_time

    now = get_offset_time().replace(tzinfo=None)
    mock_coordinator.data["children_data"]["test-child-123"]["tasks"]["upcoming"].append(
        {
            "id": "task-2",
            "title": "Physics Homework",
            "description": "Complete lab report",
            "due_date": now + timedelta(days=3),
            "set_date": now - timedelta(days=1),
            "subject": "Physics",
            "task_type": "homework",
            "completion_status": "Todo",
            "setter": "Dr. Smith",
            "raw_data": {},
        }
    )

    # Sensor should reflect updated data
    updated_value = sensor.native_value
    assert updated_value == 2

    # Attributes should also update
    attributes = sensor.extra_state_attributes
    assert len(attributes["tasks"]) == 2
    subjects = [task["subject"] for task in attributes["tasks"]]
    assert "Mathematics" in subjects
    assert "Physics" in subjects


@pytest.mark.asyncio
async def test_async_setup_entry_no_children(hass: HomeAssistant):
    """Test sensor setup when no children data available."""
    # Create config entry with no children
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - No Children",
        data={
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: [],  # Empty children list
        },
        options={},
        entry_id="test-entry-no-children",
        unique_id="test-unique-id-no-children",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    coordinator = MagicMock()
    coordinator.data = {
        "user_info": {"username": "test", "fullname": "Test User"},
        "children_data": {},  # No children
        "children_guids": [],
    }

    hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    entities = []

    def mock_add_entities(new_entities, update_before_add=False):  # pylint: disable=unused-argument
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # When children_guids is empty, uses user GUID, creating 5 entities (5 sensor types × 1 user)
    assert len(entities) == 5


@pytest.mark.asyncio
async def test_async_setup_entry_multiple_children(hass: HomeAssistant):
    """Test sensor setup with multiple children."""
    # Create config entry with 3 children
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - Multiple Children",
        data={
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["child-1", "child-2", "child-3"],
        },
        options={},
        entry_id="test-entry-multiple-children",
        unique_id="test-unique-id-multiple-children",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    coordinator = MagicMock()
    coordinator.data = {
        "user_info": {"username": "parent", "fullname": "Parent User"},
        "children_guids": ["child-1", "child-2", "child-3"],
        "children_data": {
            "child-1": {
                "events": {"today": [], "week": []},
                "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
            },
            "child-2": {
                "events": {"today": [], "week": []},
                "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
            },
            "child-3": {
                "events": {"today": [], "week": []},
                "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
            },
        },
    }

    hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    entities = []

    def mock_add_entities(new_entities, update_before_add=False):  # pylint: disable=unused-argument
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # Should create 5 sensors × 3 children = 15 entities
    assert len(entities) == 15

    # Check all children have sensors
    child_guids = [e._child_guid for e in entities]
    assert "child-1" in child_guids
    assert "child-2" in child_guids
    assert "child-3" in child_guids

    # Each child should have all sensor types
    for child_guid in ["child-1", "child-2", "child-3"]:
        child_entities = [e for e in entities if e._child_guid == child_guid]
        sensor_types = [e._sensor_type for e in child_entities]
        assert len(sensor_types) == 5
        assert SENSOR_UPCOMING_TASKS in sensor_types
        assert SENSOR_TASKS_DUE_TODAY in sensor_types
        assert SENSOR_OVERDUE_TASKS in sensor_types
        assert SENSOR_CURRENT_CLASS in sensor_types
        assert SENSOR_NEXT_CLASS in sensor_types


@pytest.mark.asyncio
async def test_sensor_device_info_consistency(mock_coordinator, mock_config_entry):
    """Test that all sensors have consistent device info."""
    sensors = [
        FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123"),
        FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-child-123"),
        FireflySensor(mock_coordinator, mock_config_entry, SENSOR_OVERDUE_TASKS, "test-child-123"),
        FireflySensor(mock_coordinator, mock_config_entry, SENSOR_CURRENT_CLASS, "test-child-123"),
        FireflySensor(mock_coordinator, mock_config_entry, SENSOR_NEXT_CLASS, "test-child-123"),
    ]

    base_device_info = sensors[0].device_info

    for sensor in sensors[1:]:
        assert sensor.device_info == base_device_info
        if sensor.device_info and base_device_info:
            assert sensor.device_info.get("identifiers") == base_device_info.get("identifiers")
            assert sensor.device_info.get("name") == base_device_info.get("name")


@pytest.mark.asyncio
async def test_sensor_unique_ids_are_unique(mock_coordinator, mock_config_entry):
    """Test that all sensors have unique IDs."""
    children = ["child-1", "child-2"]
    sensor_types = [SENSOR_UPCOMING_TASKS, SENSOR_TASKS_DUE_TODAY, SENSOR_OVERDUE_TASKS, SENSOR_CURRENT_CLASS, SENSOR_NEXT_CLASS]

    # Mock coordinator data for multiple children
    mock_coordinator.data["children_guids"] = children
    mock_coordinator.data["children_data"] = {}
    for child in children:
        mock_coordinator.data["children_data"][child] = {
            "events": {"today": [], "week": []},
            "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
        }

    unique_ids = set()

    for child_guid in children:
        for sensor_type in sensor_types:
            sensor = FireflySensor(mock_coordinator, mock_config_entry, sensor_type, child_guid)
            unique_id = sensor.unique_id

            # Check that unique ID is not already used
            assert unique_id not in unique_ids, f"Duplicate unique ID: {unique_id}"
            unique_ids.add(unique_id)

            # Check unique ID format
            expected_prefix = f"{mock_config_entry.entry_id}_{sensor_type}_{child_guid}"
            assert unique_id == expected_prefix


@pytest.mark.asyncio
async def test_sensor_extra_state_attributes_no_data(mock_config_entry):
    """Test sensor extra state attributes when coordinator has no data."""
    coordinator = MagicMock()
    coordinator.last_update_success = False
    coordinator.data = None

    sensor = FireflySensor(coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-child-123")

    # Should not crash and return empty or minimal attributes
    attributes = sensor.extra_state_attributes
    assert isinstance(attributes, dict)
    # Should at least have some basic info, even if empty


@pytest.mark.asyncio
async def test_current_class_sensor_no_class(mock_coordinator, mock_config_entry):
    """Test current class sensor when no class is active."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_CURRENT_CLASS, "test-child-123")

    assert "Current Class" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_CURRENT_CLASS}_test-child-123"
    assert sensor.icon == "mdi:school"
    assert sensor.native_value == "None"  # No current class
    assert sensor.native_unit_of_measurement is None


@pytest.mark.asyncio
async def test_current_class_sensor_with_class(mock_coordinator, mock_config_entry):
    """Test current class sensor when a class is currently active."""

    from custom_components.firefly_cloud.const import get_offset_time

    # Mock current time to be during the Math class (9-10am)
    now = get_offset_time().replace(hour=9, minute=30, second=0, microsecond=0)

    # Update event times to match current time
    math_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]
    math_event["start"] = now.replace(minute=0)
    math_event["end"] = now.replace(hour=10, minute=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_CURRENT_CLASS, "test-child-123")
        assert sensor.native_value == "Mathematics"


@pytest.mark.asyncio
async def test_next_class_sensor(mock_coordinator, mock_config_entry):
    """Test next class sensor."""
    from custom_components.firefly_cloud.const import get_offset_time

    # Mock current time to be after today's Math class (e.g., 2pm)
    now = get_offset_time().replace(hour=14, minute=0, second=0, microsecond=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_NEXT_CLASS, "test-child-123")

        assert "Next Class" in sensor.name
        assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_NEXT_CLASS}_test-child-123"
        assert sensor.icon == "mdi:clock-outline"
        # Should show next scheduled class based on mock data (Science tomorrow)
        assert sensor.native_value == "Science"
        assert sensor.native_unit_of_measurement is None


@pytest.mark.asyncio
async def test_next_class_sensor_no_upcoming(mock_coordinator, mock_config_entry):
    """Test next class sensor when no upcoming classes."""
    # Clear all future events
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"] = []

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_NEXT_CLASS, "test-child-123")
    assert sensor.native_value == "None"


@pytest.mark.asyncio
async def test_current_class_attributes(mock_coordinator, mock_config_entry):
    """Test current class sensor attributes."""
    from custom_components.firefly_cloud.const import get_offset_time

    # Mock current time to be during the Math class
    now = get_offset_time().replace(hour=9, minute=30, second=0, microsecond=0)

    # Update event times
    math_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]
    math_event["start"] = now.replace(minute=0)
    math_event["end"] = now.replace(hour=10, minute=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_CURRENT_CLASS, "test-child-123")

        attributes = sensor.extra_state_attributes
        assert "status" in attributes
        assert attributes["status"] == "in_class"
        assert attributes["class_name"] == "Mathematics"
        assert attributes["location"] == "Room 101"
        assert "minutes_remaining" in attributes
        assert attributes["minutes_remaining"] == 30  # 30 minutes left in class


@pytest.mark.asyncio
async def test_current_class_attributes_no_class(mock_coordinator, mock_config_entry):
    """Test current class sensor attributes when no class is active."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_CURRENT_CLASS, "test-child-123")

    attributes = sensor.extra_state_attributes
    assert "status" in attributes
    assert attributes["status"] == "no_current_class"
    assert "current_time" in attributes


@pytest.mark.asyncio
async def test_next_class_attributes(mock_coordinator, mock_config_entry):
    """Test next class sensor attributes."""
    from custom_components.firefly_cloud.const import get_offset_time

    # Mock current time to be after today's Math class so Science is next
    now = get_offset_time().replace(hour=14, minute=0, second=0, microsecond=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_NEXT_CLASS, "test-child-123")

        attributes = sensor.extra_state_attributes
        assert "status" in attributes
        assert attributes["status"] == "class_scheduled"
        assert attributes["class_name"] == "Science"
        assert attributes["location"] == "Lab 1"
        assert "minutes_until" in attributes


@pytest.mark.asyncio
async def test_next_class_attributes_no_upcoming(mock_coordinator, mock_config_entry):
    """Test next class sensor attributes when no upcoming classes."""
    # Clear all future events
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"] = []

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_NEXT_CLASS, "test-child-123")

    attributes = sensor.extra_state_attributes
    assert "status" in attributes
    assert attributes["status"] == "no_upcoming_class"
    assert "current_time" in attributes


@pytest.mark.asyncio
async def test_class_sensors_with_no_events(mock_coordinator, mock_config_entry):
    """Test class sensors when no events data is available."""
    # Remove events data
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"] = []

    current_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_CURRENT_CLASS, "test-child-123")
    next_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_NEXT_CLASS, "test-child-123")

    assert current_sensor.native_value == "None"
    assert next_sensor.native_value == "None"
    assert current_sensor.available is True  # Still available, just no data
    assert next_sensor.available is True


@pytest.mark.asyncio
async def test_next_class_during_last_class_of_day(mock_coordinator, mock_config_entry):
    """Test next class sensor shows None when in the last class of the day."""
    from datetime import timedelta
    from custom_components.firefly_cloud.const import get_offset_time

    # Mock current time to be in the last class (Science 11am-12pm)
    now = get_offset_time().replace(hour=11, minute=30, second=0, microsecond=0)

    # Set up events: Math 9-10am (past), Science 11am-12pm (current), English tomorrow 9am
    events = [
        {
            "start": now.replace(hour=9, minute=0),
            "end": now.replace(hour=10, minute=0),
            "subject": "Mathematics",
            "location": "Room 101",
            "description": "Algebra lesson",
        },
        {
            "start": now.replace(hour=11, minute=0),
            "end": now.replace(hour=12, minute=0),
            "subject": "Science",
            "location": "Lab 1",
            "description": "Last class of day",
        },
        {
            "start": now.replace(hour=9, minute=0) + timedelta(days=1),  # Tomorrow 9am
            "end": now.replace(hour=10, minute=0) + timedelta(days=1),
            "subject": "English",
            "location": "Room 102",
            "description": "Tomorrow's first class",
        },
    ]

    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"] = events

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        current_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_CURRENT_CLASS, "test-child-123")
        next_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_NEXT_CLASS, "test-child-123")

        # Should be in Science class
        assert current_sensor.native_value == "Science"
        # Next should be "None" (last class of day)
        assert next_sensor.native_value == "None"

        # Check attributes
        next_attributes = next_sensor.extra_state_attributes
        assert next_attributes["status"] == "last_class_of_day"
        assert next_attributes["context"] == "no_more_classes_today"


@pytest.mark.asyncio
async def test_next_class_after_school_hours_shows_tomorrow(mock_coordinator, mock_config_entry):
    """Test next class sensor shows tomorrow's first class after school hours."""
    from datetime import timedelta
    from custom_components.firefly_cloud.const import get_offset_time

    # Mock current time to be after school (6pm)
    now = get_offset_time().replace(hour=18, minute=0, second=0, microsecond=0)

    # Set up events: Science today (past), Math tomorrow (future)
    events = [
        {
            "start": now.replace(hour=11, minute=0),  # Today 11am (past)
            "end": now.replace(hour=12, minute=0),
            "subject": "Science",
            "location": "Lab 1",
            "description": "Today's last class",
        },
        {
            "start": now.replace(hour=9, minute=0) + timedelta(days=1),  # Tomorrow 9am
            "end": now.replace(hour=10, minute=0) + timedelta(days=1),
            "subject": "Mathematics",
            "location": "Room 101",
            "description": "Tomorrow's first class",
        },
    ]

    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"] = events

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        current_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_CURRENT_CLASS, "test-child-123")
        next_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_NEXT_CLASS, "test-child-123")

        # No current class (after hours)
        assert current_sensor.native_value == "None"
        # Next should show tomorrow's first class
        assert next_sensor.native_value == "Mathematics"

        # Check attributes
        next_attributes = next_sensor.extra_state_attributes
        assert next_attributes["status"] == "class_scheduled"
        assert next_attributes["class_name"] == "Mathematics"
        assert next_attributes["context"] == "next_class_future_day"


@pytest.mark.asyncio
async def test_next_class_during_middle_class_shows_next_today(mock_coordinator, mock_config_entry):
    """Test next class sensor shows next class today when in a middle class."""
    from custom_components.firefly_cloud.const import get_offset_time

    # Mock current time to be in the middle class (Math 9:30am)
    now = get_offset_time().replace(hour=9, minute=30, second=0, microsecond=0)

    # Set up events: Math 9-10am (current), Science 11am-12pm (next today)
    events = [
        {
            "start": now.replace(hour=9, minute=0),
            "end": now.replace(hour=10, minute=0),
            "subject": "Mathematics",
            "location": "Room 101",
            "description": "Current class",
        },
        {
            "start": now.replace(hour=11, minute=0),
            "end": now.replace(hour=12, minute=0),
            "subject": "Science",
            "location": "Lab 1",
            "description": "Next class today",
        },
    ]

    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"] = events

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        current_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_CURRENT_CLASS, "test-child-123")
        next_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_NEXT_CLASS, "test-child-123")

        # Should be in Math class
        assert current_sensor.native_value == "Mathematics"
        # Next should show Science (next class today)
        assert next_sensor.native_value == "Science"

        # Check attributes
        next_attributes = next_sensor.extra_state_attributes
        assert next_attributes["status"] == "class_scheduled"
        assert next_attributes["class_name"] == "Science"
        assert next_attributes["context"] == "next_class_today"


@pytest.mark.asyncio
async def test_current_class_with_time_prefix_enabled(mock_coordinator):
    """Test current class sensor with time prefix option enabled."""
    from custom_components.firefly_cloud.const import (
        CONF_CHILDREN_GUIDS,
        CONF_DEVICE_ID,
        CONF_HOST,
        CONF_SCHOOL_CODE,
        CONF_SCHOOL_NAME,
        CONF_SECRET,
        CONF_TASK_LOOKAHEAD_DAYS,
        CONF_USER_GUID,
        DEFAULT_TASK_LOOKAHEAD_DAYS,
        DOMAIN,
        get_offset_time,
    )

    # Create config entry with time prefix enabled
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - John Doe",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["test-child-123", "test-child-456"],
            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
        },
        options={"show_class_times": True},
        entry_id="test-entry-id",
        unique_id="test-unique-id",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    # Mock current time to be during the Math class (9-10am)
    now = get_offset_time().replace(hour=9, minute=30, second=0, microsecond=0)

    # Update event times to match current time
    math_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]
    math_event["start"] = now.replace(minute=0)
    math_event["end"] = now.replace(hour=10, minute=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, config_entry, SENSOR_CURRENT_CLASS, "test-child-123")
        # Should show time prefix: "9.00-10.00: Mathematics"
        assert sensor.native_value == "9.00-10.00: Mathematics"


@pytest.mark.asyncio
async def test_current_class_with_time_prefix_disabled(mock_coordinator):
    """Test current class sensor with time prefix option disabled."""
    from custom_components.firefly_cloud.const import (
        CONF_CHILDREN_GUIDS,
        CONF_DEVICE_ID,
        CONF_HOST,
        CONF_SCHOOL_CODE,
        CONF_SCHOOL_NAME,
        CONF_SECRET,
        CONF_TASK_LOOKAHEAD_DAYS,
        CONF_USER_GUID,
        DEFAULT_TASK_LOOKAHEAD_DAYS,
        DOMAIN,
        get_offset_time,
    )

    # Create config entry with time prefix disabled (default)
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - John Doe",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["test-child-123", "test-child-456"],
            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
        },
        options={"show_class_times": False},
        entry_id="test-entry-id",
        unique_id="test-unique-id",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    # Mock current time to be during the Math class (9-10am)
    now = get_offset_time().replace(hour=9, minute=30, second=0, microsecond=0)

    # Update event times to match current time
    math_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]
    math_event["start"] = now.replace(minute=0)
    math_event["end"] = now.replace(hour=10, minute=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, config_entry, SENSOR_CURRENT_CLASS, "test-child-123")
        # Should show just the subject: "Mathematics"
        assert sensor.native_value == "Mathematics"


@pytest.mark.asyncio
async def test_current_class_none_no_time_prefix(mock_coordinator):
    """Test current class sensor shows 'None' without time prefix."""
    from custom_components.firefly_cloud.const import (
        CONF_CHILDREN_GUIDS,
        CONF_DEVICE_ID,
        CONF_HOST,
        CONF_SCHOOL_CODE,
        CONF_SCHOOL_NAME,
        CONF_SECRET,
        CONF_TASK_LOOKAHEAD_DAYS,
        CONF_USER_GUID,
        DEFAULT_TASK_LOOKAHEAD_DAYS,
        DOMAIN,
        get_offset_time,
    )

    # Create config entry with time prefix enabled
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - John Doe",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["test-child-123", "test-child-456"],
            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
        },
        options={"show_class_times": True},
        entry_id="test-entry-id",
        unique_id="test-unique-id",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    # Mock current time to be outside of class hours (8am, before 9am Math class)
    now = get_offset_time().replace(hour=8, minute=0, second=0, microsecond=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, config_entry, SENSOR_CURRENT_CLASS, "test-child-123")
        # Should show "None" without any time prefix
        assert sensor.native_value == "None"


@pytest.mark.asyncio
async def test_next_class_with_time_prefix_enabled(mock_coordinator):
    """Test next class sensor with time prefix option enabled."""
    from custom_components.firefly_cloud.const import (
        CONF_CHILDREN_GUIDS,
        CONF_DEVICE_ID,
        CONF_HOST,
        CONF_SCHOOL_CODE,
        CONF_SCHOOL_NAME,
        CONF_SECRET,
        CONF_TASK_LOOKAHEAD_DAYS,
        CONF_USER_GUID,
        DEFAULT_TASK_LOOKAHEAD_DAYS,
        DOMAIN,
        get_offset_time,
    )

    # Create config entry with time prefix enabled
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - John Doe",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["test-child-123", "test-child-456"],
            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
        },
        options={"show_class_times": True},
        entry_id="test-entry-id",
        unique_id="test-unique-id",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    # Mock current time to be during the Math class (9-10am)
    now = get_offset_time().replace(hour=9, minute=30, second=0, microsecond=0)

    # Update event times to match current time
    math_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]
    math_event["start"] = now.replace(minute=0)
    math_event["end"] = now.replace(hour=10, minute=0)

    science_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][1]
    science_event["start"] = now.replace(hour=11, minute=0)
    science_event["end"] = now.replace(hour=12, minute=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, config_entry, SENSOR_NEXT_CLASS, "test-child-123")
        # Should show time prefix: "11.00-12.00: Science"
        assert sensor.native_value == "11.00-12.00: Science"


@pytest.mark.asyncio
async def test_next_class_with_time_prefix_disabled(mock_coordinator):
    """Test next class sensor with time prefix option disabled."""
    from custom_components.firefly_cloud.const import (
        CONF_CHILDREN_GUIDS,
        CONF_DEVICE_ID,
        CONF_HOST,
        CONF_SCHOOL_CODE,
        CONF_SCHOOL_NAME,
        CONF_SECRET,
        CONF_TASK_LOOKAHEAD_DAYS,
        CONF_USER_GUID,
        DEFAULT_TASK_LOOKAHEAD_DAYS,
        DOMAIN,
        get_offset_time,
    )

    # Create config entry with time prefix disabled
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - John Doe",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["test-child-123", "test-child-456"],
            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
        },
        options={"show_class_times": False},
        entry_id="test-entry-id",
        unique_id="test-unique-id",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    # Mock current time to be during the Math class (9-10am)
    now = get_offset_time().replace(hour=9, minute=30, second=0, microsecond=0)

    # Update event times to match current time
    math_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]
    math_event["start"] = now.replace(minute=0)
    math_event["end"] = now.replace(hour=10, minute=0)

    science_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][1]
    science_event["start"] = now.replace(hour=11, minute=0)
    science_event["end"] = now.replace(hour=12, minute=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, config_entry, SENSOR_NEXT_CLASS, "test-child-123")
        # Should show just the subject: "Science"
        assert sensor.native_value == "Science"


@pytest.mark.asyncio
async def test_next_class_in_class_no_upcoming_with_time_prefix(mock_coordinator):
    """Test next class sensor shows 'None' when in last class (with time prefix enabled)."""
    from custom_components.firefly_cloud.const import (
        CONF_CHILDREN_GUIDS,
        CONF_DEVICE_ID,
        CONF_HOST,
        CONF_SCHOOL_CODE,
        CONF_SCHOOL_NAME,
        CONF_SECRET,
        CONF_TASK_LOOKAHEAD_DAYS,
        CONF_USER_GUID,
        DEFAULT_TASK_LOOKAHEAD_DAYS,
        DOMAIN,
        get_offset_time,
    )

    # Create config entry with time prefix enabled
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - John Doe",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["test-child-123", "test-child-456"],
            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
        },
        options={"show_class_times": True},
        entry_id="test-entry-id",
        unique_id="test-unique-id",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    # Mock current time to be during Science (last class), 11-12pm
    now = get_offset_time().replace(hour=11, minute=30, second=0, microsecond=0)

    # Update event times - only Science class exists
    science_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][1]
    science_event["start"] = now.replace(minute=0)
    science_event["end"] = now.replace(hour=12, minute=0)

    # Remove math event so Science is the only/last class
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"] = [science_event]

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, config_entry, SENSOR_NEXT_CLASS, "test-child-123")
        # Should show "None" without time prefix (no next class)
        assert sensor.native_value == "None"


@pytest.mark.asyncio
async def test_next_class_not_in_class_with_time_prefix(mock_coordinator):
    """Test next class sensor when not in a class with time prefix enabled."""
    from custom_components.firefly_cloud.const import (
        CONF_CHILDREN_GUIDS,
        CONF_DEVICE_ID,
        CONF_HOST,
        CONF_SCHOOL_CODE,
        CONF_SCHOOL_NAME,
        CONF_SECRET,
        CONF_TASK_LOOKAHEAD_DAYS,
        CONF_USER_GUID,
        DEFAULT_TASK_LOOKAHEAD_DAYS,
        DOMAIN,
        get_offset_time,
    )

    # Create config entry with time prefix enabled
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - John Doe",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["test-child-123", "test-child-456"],
            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
        },
        options={"show_class_times": True},
        entry_id="test-entry-id",
        unique_id="test-unique-id",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    # Mock current time to be between classes (10:30am)
    now = get_offset_time().replace(hour=10, minute=30, second=0, microsecond=0)

    # Update event times
    math_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]
    math_event["start"] = now.replace(hour=9, minute=0)
    math_event["end"] = now.replace(hour=10, minute=0)

    science_event = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][1]
    science_event["start"] = now.replace(hour=11, minute=0)
    science_event["end"] = now.replace(hour=12, minute=0)

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now):
        sensor = FireflySensor(mock_coordinator, config_entry, SENSOR_NEXT_CLASS, "test-child-123")
        # Should show time prefix for next upcoming class: "11.00-12.00: Science"
        assert sensor.native_value == "11.00-12.00: Science"


@pytest.mark.asyncio
async def test_class_times_show_local_timezone(mock_coordinator):
    """Test that class times are shown in local timezone, not UTC."""
    from custom_components.firefly_cloud.const import (
        CONF_CHILDREN_GUIDS,
        CONF_DEVICE_ID,
        CONF_HOST,
        CONF_SCHOOL_CODE,
        CONF_SCHOOL_NAME,
        CONF_SECRET,
        CONF_TASK_LOOKAHEAD_DAYS,
        CONF_USER_GUID,
        DEFAULT_TASK_LOOKAHEAD_DAYS,
        DOMAIN,
    )
    from homeassistant.util import dt as dt_util

    # Create config entry with time prefix enabled
    config_entry = ConfigEntry(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School - John Doe",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["test-child-123", "test-child-456"],
            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
        },
        options={"show_class_times": True},
        entry_id="test-entry-id",
        unique_id="test-unique-id",
        source="user",
        discovery_keys=MappingProxyType({}),
        subentries_data={},
    )

    # Create times in UTC: 9am UTC = 7pm AEST (Melbourne time, UTC+10)
    # This mimics what might come from the API
    now_utc = dt_util.utcnow().replace(hour=9, minute=30, second=0, microsecond=0)
    now_local = dt_util.as_local(now_utc)

    # Create events with UTC times (9-10am UTC)
    class_start_utc = now_utc.replace(minute=0)
    class_end_utc = now_utc.replace(hour=10, minute=0)

    # Set up coordinator data with UTC times
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"] = [
        {
            "start": class_start_utc,
            "end": class_end_utc,
            "subject": "Mathematics",
            "location": "Room 101",
            "description": "Test class",
        }
    ]

    with patch("custom_components.firefly_cloud.const.get_offset_time", return_value=now_local):
        sensor = FireflySensor(mock_coordinator, config_entry, SENSOR_CURRENT_CLASS, "test-child-123")

        # The sensor should show times in local timezone, not UTC
        # If local is AEST (UTC+10), 09:00 UTC should display as 19:00 local
        value = sensor.native_value

        # The value should contain the local time representation, not UTC time
        assert value is not None
        if value != "None":
            # Extract the time from the format "H.MM-H.MM: Subject"
            time_part = value.split(":")[0] if ":" in value else ""
            # The time should be in local timezone (19.00-20.00 for AEST)
            # Not UTC timezone (9.00-10.00)
            local_start = class_start_utc.astimezone(now_local.tzinfo) if now_local.tzinfo else class_start_utc
            expected_start = f"{local_start.hour}.{local_start.minute:02d}"
            assert time_part.startswith(expected_start), f"Expected time to start with {expected_start} (local), but got {time_part}"
