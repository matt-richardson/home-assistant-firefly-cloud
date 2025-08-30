"""Test the Firefly Cloud sensor platform."""
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest
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
)


@pytest.fixture
def mock_coordinator():
    """Return a mock coordinator with data."""
    coordinator = AsyncMock()
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
                }
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
        "last_updated": now,
    }
    
    coordinator.last_update_success = True
    coordinator.last_exception = None
    return coordinator


@pytest.mark.asyncio
async def test_async_setup_entry(hass: HomeAssistant, mock_config_entry, mock_coordinator):
    """Test sensor platform setup."""
    hass.data = {DOMAIN: {mock_config_entry.entry_id: mock_coordinator}}
    
    entities = []
    
    def mock_add_entities(entity_list, update_before_add=True):
        entities.extend(entity_list)
    
    await async_setup_entry(hass, mock_config_entry, mock_add_entities)
    
    assert len(entities) == 4
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
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE)
    
    assert "Today's Schedule" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_TODAY_SCHEDULE}"
    assert sensor.icon == "mdi:calendar-today"
    assert sensor.native_value == 1
    assert sensor.native_unit_of_measurement == "classes"


@pytest.mark.asyncio
async def test_week_schedule_sensor(mock_coordinator, mock_config_entry):
    """Test week schedule sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_WEEK_SCHEDULE)
    
    assert "Week Schedule" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_WEEK_SCHEDULE}"
    assert sensor.icon == "mdi:calendar-week"
    assert sensor.native_value == 2
    assert sensor.native_unit_of_measurement == "classes"


@pytest.mark.asyncio
async def test_upcoming_tasks_sensor(mock_coordinator, mock_config_entry):
    """Test upcoming tasks sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_UPCOMING_TASKS)
    
    assert "Upcoming Tasks" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_UPCOMING_TASKS}"
    assert sensor.icon == "mdi:clipboard-text"
    assert sensor.native_value == 1
    assert sensor.native_unit_of_measurement == "tasks"


@pytest.mark.asyncio
async def test_tasks_due_today_sensor(mock_coordinator, mock_config_entry):
    """Test tasks due today sensor."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY)
    
    assert "Tasks Due Today" in sensor.name
    assert sensor.unique_id == f"{mock_config_entry.entry_id}_{SENSOR_TASKS_DUE_TODAY}"
    assert sensor.icon == "mdi:clipboard-alert"
    assert sensor.native_value == 0
    assert sensor.native_unit_of_measurement == "tasks"


@pytest.mark.asyncio
async def test_tasks_due_today_sensor_with_tasks(mock_coordinator, mock_config_entry):
    """Test tasks due today sensor with tasks."""
    now = datetime.now()
    mock_coordinator.data["tasks"]["due_today"] = [
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
    
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TASKS_DUE_TODAY)
    
    assert sensor.native_value == 1


@pytest.mark.asyncio
async def test_sensor_availability(mock_coordinator, mock_config_entry):
    """Test sensor availability."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE)
    
    # Available when coordinator has successful update
    mock_coordinator.last_update_success = True
    mock_coordinator.data = {"some": "data"}
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
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE)
    
    device_info = sensor.device_info
    assert device_info["identifiers"] == {(DOMAIN, mock_config_entry.entry_id)}
    assert "Firefly Cloud" in device_info["name"]
    assert device_info["manufacturer"] == "Firefly Learning"
    assert device_info["model"] == "Firefly Cloud Integration"


@pytest.mark.asyncio
async def test_sensor_no_coordinator_data(mock_config_entry):
    """Test sensor with no coordinator data."""
    coordinator = AsyncMock()
    coordinator.data = None
    coordinator.last_update_success = False
    
    sensor = FireflySensor(coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE)
    
    assert sensor.available is False
    assert sensor.native_value is None


@pytest.mark.asyncio
async def test_sensor_extra_state_attributes(mock_coordinator, mock_config_entry):
    """Test sensor extra state attributes."""
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE)
    
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
        "events": {},  # Missing today/week keys
        "tasks": {},   # Missing task type keys
        "last_updated": datetime.now(),
    }
    
    sensor = FireflySensor(mock_coordinator, mock_config_entry, SENSOR_TODAY_SCHEDULE)
    
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