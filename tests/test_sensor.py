"""Test the Firefly Cloud sensor platform."""

from datetime import datetime, timedelta
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from custom_components.firefly_cloud.sensor import (
    FireflySensor,
    async_setup_entry,
)
from custom_components.firefly_cloud.const import (
    DOMAIN,
    SENSOR_TODAY_SCHEDULE,
    SENSOR_WEEK_SCHEDULE,
    SENSOR_UPCOMING_TASKS,
    SENSOR_TASKS_DUE_TODAY,
    SENSOR_TYPES,
    CONF_SCHOOL_NAME,
    CONF_HOST,
    CONF_DEVICE_ID,
    CONF_SECRET,
    CONF_USER_GUID,
    CONF_CHILDREN_GUIDS,
)


@pytest.fixture
def mock_coordinator():
    """Return a mock coordinator with data."""
    coordinator = MagicMock()
    now = datetime.now()

    # Mock coordinator data
    coordinator.data = {
        "user_info": {
            "username": "john.doe",
            "fullname": "John Doe",
            "email": "john.doe@test.com",
            "role": "student",
            "guid": "test-user-123",
        },
        "children_guids": ["test-user-123"],
        "children_data": {
            "test-user-123": {
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
            }
        },
        "last_updated": now,
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

    assert len(entities) == 8  # 4 sensor types × 2 children
    assert all(isinstance(e, FireflySensor) for e in entities)

    # Check that all sensor types are created
    sensor_types = [e._sensor_type for e in entities]
    assert SENSOR_TODAY_SCHEDULE in sensor_types
    assert SENSOR_WEEK_SCHEDULE in sensor_types
    assert SENSOR_UPCOMING_TASKS in sensor_types
    assert SENSOR_TASKS_DUE_TODAY in sensor_types


@pytest.mark.asyncio
async def test_today_schedule_sensor(mock_coordinator, mock_config_entry):
    """Test today schedule sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    assert "Today's Schedule" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_TODAY_SCHEDULE}_test-user-123"
    assert sensor.icon == "mdi:calendar-today"
    assert sensor.native_value == 1
    assert sensor.native_unit_of_measurement == "classes"


@pytest.mark.asyncio
async def test_week_schedule_sensor(mock_coordinator, mock_config_entry):
    """Test week schedule sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_WEEK_SCHEDULE, "test-user-123")

    assert "Week Schedule" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_WEEK_SCHEDULE}_test-user-123"
    assert sensor.icon == "mdi:calendar-week"
    assert sensor.native_value == 2
    assert sensor.native_unit_of_measurement == "classes"


@pytest.mark.asyncio
async def test_upcoming_tasks_sensor(mock_coordinator, mock_config_entry):
    """Test upcoming tasks sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-user-123")

    assert "Upcoming Tasks" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_UPCOMING_TASKS}_test-user-123"
    assert sensor.icon == "mdi:clipboard-text"
    assert sensor.native_value == 1
    assert sensor.native_unit_of_measurement == "tasks"


@pytest.mark.asyncio
async def test_tasks_due_today_sensor(mock_coordinator, mock_config_entry):
    """Test tasks due today sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-user-123")

    assert "Tasks Due Today" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_TASKS_DUE_TODAY}_test-user-123"
    assert sensor.icon == "mdi:clipboard-alert"
    assert sensor.native_value == 0
    assert sensor.native_unit_of_measurement == "tasks"


@pytest.mark.asyncio
async def test_tasks_due_today_sensor_with_tasks(mock_coordinator, mock_config_entry):
    """Test tasks due today sensor with tasks."""
    now = datetime.now()
    mock_coordinator.data["children_data"]["test-user-123"]["tasks"]["due_today"] = [
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

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-user-123")

    assert sensor.native_value == 1


@pytest.mark.asyncio
async def test_sensor_availability(mock_coordinator, mock_config_entry):
    """Test sensor availability."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    # Available when coordinator has successful update and child data exists
    mock_coordinator.last_update_success = True
    mock_coordinator.data = {"children_data": {"test-user-123": {"some": "data"}}}
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
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

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

    sensor = FireflySensor(coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    assert sensor.available is False
    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_sensor_extra_state_attributes(mock_coordinator, mock_config_entry):
    """Test sensor extra state attributes."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    attributes = sensor.extra_state_attributes
    assert isinstance(attributes, dict)
    # Should include data relevant to the sensor type
    assert len(attributes) > 1  # Should have meaningful attributes
    assert "last_updated" in attributes


@pytest.mark.asyncio
async def test_sensor_handles_missing_data_gracefully(mock_coordinator, mock_config_entry):
    """Test sensor handles missing data gracefully."""
    # Remove specific data that sensor needs
    mock_coordinator.data = {
        "user_info": {"username": "test", "fullname": "Test User", "guid": "test-123"},
        "children_data": {
            "test-user-123": {
                "events": {},  # Missing today/week keys
                "tasks": {},  # Missing task type keys
            }
        },
        "last_updated": datetime.now(),
    }

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    # Should not crash and return sensible defaults
    assert sensor.available is True
    assert sensor.native_value == 0  # Default when no data


@pytest.mark.asyncio
async def test_all_sensor_types_defined():
    """Test that all sensor types have proper configuration."""
    for sensor_type in [SENSOR_TODAY_SCHEDULE, SENSOR_WEEK_SCHEDULE, SENSOR_UPCOMING_TASKS, SENSOR_TASKS_DUE_TODAY]:
        assert sensor_type in SENSOR_TYPES
        config = SENSOR_TYPES[sensor_type]
        assert "name" in config
        assert "icon" in config
        assert "unit" in config
        assert "device_class" in config


@pytest.mark.asyncio
async def test_sensor_with_nonexistent_child(mock_coordinator, mock_config_entry):
    """Test sensor with child GUID that doesn't exist in data."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "nonexistent-child-123")

    assert sensor.available is False
    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_sensor_attributes_today_schedule(mock_coordinator, mock_config_entry):
    """Test today schedule sensor attributes."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    attributes = sensor.extra_state_attributes
    assert "classes" in attributes
    assert "current_class" in attributes
    assert "last_updated" in attributes

    # Check class details
    classes = attributes["classes"]
    assert len(classes) == 1
    assert classes[0]["subject"] == "Mathematics"
    assert classes[0]["location"] == "Room 101"


@pytest.mark.asyncio
async def test_sensor_attributes_week_schedule(mock_coordinator, mock_config_entry):
    """Test week schedule sensor attributes."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_WEEK_SCHEDULE, "test-user-123")

    attributes = sensor.extra_state_attributes
    assert "schedule_by_day" in attributes
    assert "special_days" in attributes
    assert "total_classes_this_week" in attributes
    assert "last_updated" in attributes

    # Check schedule details
    schedule_by_day = attributes["schedule_by_day"]
    assert isinstance(schedule_by_day, dict)
    # Should have entries for all 7 days of the week
    assert len(schedule_by_day) == 7


@pytest.mark.asyncio
async def test_sensor_attributes_upcoming_tasks(mock_coordinator, mock_config_entry):
    """Test upcoming tasks sensor attributes."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-user-123")

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
    now = datetime.now()

    # Add task due today to coordinator data
    mock_coordinator.data["children_data"]["test-user-123"]["tasks"]["due_today"] = [
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

    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-user-123")

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
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    assert hasattr(sensor, "state_class")
    assert hasattr(sensor, "device_class")

    # Check that properties match sensor type configuration
    sensor_config = SENSOR_TYPES[SENSOR_TODAY_SCHEDULE]
    if "state_class" in sensor_config:
        assert sensor.state_class == sensor_config["state_class"]
    if "device_class" in sensor_config:
        assert sensor.device_class == sensor_config["device_class"]


@pytest.mark.asyncio
async def test_sensor_entity_category(mock_coordinator, mock_config_entry):
    """Test sensor entity category if defined."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    # Entity category should be None for main sensors (they're not diagnostic/config)
    assert sensor.entity_category is None


@pytest.mark.asyncio
async def test_sensor_handles_empty_events(mock_coordinator, mock_config_entry):
    """Test sensor handling empty events gracefully."""
    # Clear events data
    mock_coordinator.data["children_data"]["test-user-123"]["events"]["today"] = []
    mock_coordinator.data["children_data"]["test-user-123"]["events"]["week"] = []

    today_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")
    week_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_WEEK_SCHEDULE, "test-user-123")

    assert today_sensor.native_value == 0
    assert week_sensor.native_value == 0
    assert today_sensor.available is True
    assert week_sensor.available is True

    # Check attributes don't break
    today_attrs = today_sensor.extra_state_attributes
    week_attrs = week_sensor.extra_state_attributes

    assert today_attrs["classes"] == []
    assert week_attrs["schedule_by_day"] is not None


@pytest.mark.asyncio
async def test_sensor_handles_empty_tasks(mock_coordinator, mock_config_entry):
    """Test sensor handling empty tasks gracefully."""
    # Clear tasks data
    mock_coordinator.data["children_data"]["test-user-123"]["tasks"]["upcoming"] = []
    mock_coordinator.data["children_data"]["test-user-123"]["tasks"]["due_today"] = []

    upcoming_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-user-123")
    due_today_sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-user-123")

    assert upcoming_sensor.native_value == 0
    assert due_today_sensor.native_value == 0
    assert upcoming_sensor.available is True
    assert due_today_sensor.available is True

    # Check attributes don't break
    upcoming_attrs = upcoming_sensor.extra_state_attributes
    due_today_attrs = due_today_sensor.extra_state_attributes

    assert upcoming_attrs["tasks"] == []
    assert due_today_attrs["tasks"] == []


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

    sensor = FireflySensor(coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "child-123")

    assert "John Doe" in sensor.name
    assert "Today's Schedule" in sensor.name


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

    sensor = FireflySensor(coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "child-123")

    assert "child-12" in sensor.name  # First 8 chars of "child-123"
    assert "Today's Schedule" in sensor.name


@pytest.mark.asyncio
async def test_sensor_coordinator_data_update(mock_coordinator, mock_config_entry):
    """Test sensor updates when coordinator data changes."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    initial_value = sensor.native_value
    assert initial_value == 1

    # Update coordinator data
    now = datetime.now()
    mock_coordinator.data["children_data"]["test-user-123"]["events"]["today"].append(
        {
            "start": now.replace(hour=14, minute=0, second=0, microsecond=0),
            "end": now.replace(hour=15, minute=0, second=0, microsecond=0),
            "subject": "Physics",
            "location": "Lab 2",
            "description": "Physics experiment",
            "guild": None,
            "attendees": [],
        }
    )

    # Sensor should reflect updated data
    updated_value = sensor.native_value
    assert updated_value == 2

    # Attributes should also update
    attributes = sensor.extra_state_attributes
    assert len(attributes["classes"]) == 2
    subjects = [event["subject"] for event in attributes["classes"]]
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

    # When children_guids is empty, uses user GUID, creating 4 entities (4 sensor types × 1 user)
    assert len(entities) == 4


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

    # Should create 4 sensors × 3 children = 12 entities
    assert len(entities) == 12

    # Check all children have sensors
    child_guids = [e._child_guid for e in entities]
    assert "child-1" in child_guids
    assert "child-2" in child_guids
    assert "child-3" in child_guids

    # Each child should have all sensor types
    for child_guid in ["child-1", "child-2", "child-3"]:
        child_entities = [e for e in entities if e._child_guid == child_guid]
        sensor_types = [e._sensor_type for e in child_entities]
        assert len(sensor_types) == 4
        assert SENSOR_TODAY_SCHEDULE in sensor_types
        assert SENSOR_WEEK_SCHEDULE in sensor_types
        assert SENSOR_UPCOMING_TASKS in sensor_types
        assert SENSOR_TASKS_DUE_TODAY in sensor_types


@pytest.mark.asyncio
async def test_sensor_device_info_consistency(mock_coordinator, mock_config_entry):
    """Test that all sensors have consistent device info."""
    sensors = [
        FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123"),
        FireflySensor(mock_coordinator, mock_config_entry, SENSOR_WEEK_SCHEDULE, "test-user-123"),
        FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS, "test-user-123"),
        FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY, "test-user-123"),
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
    sensor_types = [SENSOR_TODAY_SCHEDULE, SENSOR_WEEK_SCHEDULE, SENSOR_UPCOMING_TASKS, SENSOR_TASKS_DUE_TODAY]

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

    sensor = FireflySensor(coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE, "test-user-123")

    # Should not crash and return empty or minimal attributes
    attributes = sensor.extra_state_attributes
    assert isinstance(attributes, dict)
    # Should at least have some basic info, even if empty
