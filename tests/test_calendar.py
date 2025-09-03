"""Test the Firefly Cloud calendar platform."""

from datetime import datetime, timedelta
from types import MappingProxyType
from unittest.mock import MagicMock

import pytest
from homeassistant.components.calendar import CalendarEvent
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.firefly_cloud.calendar import (
    FireflyCalendar,
    async_setup_entry,
)
from custom_components.firefly_cloud.const import (
    CONF_CHILDREN_GUIDS,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_SCHOOL_NAME,
    CONF_SECRET,
    CONF_USER_GUID,
    DOMAIN,
)


@pytest.fixture
def mock_coordinator():
    """Return a mock coordinator with calendar data."""
    coordinator = MagicMock()
    now = dt_util.now()

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
                    "week": [
                        {
                            "start": now.replace(hour=9, minute=0, second=0, microsecond=0),
                            "end": now.replace(hour=10, minute=0, second=0, microsecond=0),
                            "subject": "Mathematics",
                            "location": "Room 101",
                            "description": "Algebra lesson",
                            "guild": "Year 10",
                            "attendees": ["Mr. Smith"],
                        },
                        {
                            "start": now.replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1),
                            "end": now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1),
                            "subject": "Science",
                            "location": "Lab 1",
                            "description": "Chemistry experiment",
                            "guild": "Year 10",
                            "attendees": ["Ms. Johnson"],
                        },
                    ]
                },
                "tasks": {
                    "all": [],
                    "due_today": [],
                    "upcoming": [],
                    "overdue": [],
                },
            },
            "test-child-456": {
                "name": "Jane Doe", 
                "events": {
                    "week": []
                },
                "tasks": {
                    "all": [],
                    "due_today": [],
                    "upcoming": [],
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
    """Test calendar platform setup."""
    hass.data[DOMAIN] = {mock_config_entry.entry_id: mock_coordinator}

    entities = []

    def mock_add_entities(new_entities, update_before_add=False):  # pylint: disable=unused-argument
        entities.extend(new_entities)

    await async_setup_entry(hass, mock_config_entry, mock_add_entities)

    assert len(entities) == 2  # 1 calendar entity per child (2 children in config)
    assert all(isinstance(e, FireflyCalendar) for e in entities)


@pytest.mark.asyncio
async def test_calendar_properties(mock_coordinator, mock_config_entry):
    """Test calendar basic properties."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    assert "Schedule" in calendar.name
    assert calendar.unique_id == f"{mock_config_entry.entry_id}_calendar_test-child-123"
    assert calendar.icon == "mdi:calendar-month"


@pytest.mark.asyncio
async def test_calendar_availability(mock_coordinator, mock_config_entry):
    """Test calendar availability."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Available when coordinator has successful update and child data exists
    mock_coordinator.last_update_success = True
    mock_coordinator.data = {"children_data": {"test-child-123": {"some": "data"}}}
    assert calendar.available is True

    # Unavailable when coordinator update failed
    mock_coordinator.last_update_success = False
    assert calendar.available is False

    # Unavailable when no data
    mock_coordinator.last_update_success = True
    mock_coordinator.data = None
    assert calendar.available is False


@pytest.mark.asyncio
async def test_calendar_current_event(mock_coordinator, mock_config_entry):
    """Test calendar current event property."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Mock current time to be during first event
    now = dt_util.now()
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]["start"] = now - timedelta(minutes=30)
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]["end"] = now + timedelta(minutes=30)

    event = calendar.event
    assert event is not None
    assert isinstance(event, CalendarEvent)
    assert event.summary == "Mathematics"
    assert event.location == "Room 101"


@pytest.mark.asyncio 
async def test_calendar_next_event(mock_coordinator, mock_config_entry):
    """Test calendar next event when no current event."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Mock both events to be in the future
    now = dt_util.now()
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]["start"] = now + timedelta(hours=1)
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]["end"] = now + timedelta(hours=2)

    event = calendar.event
    assert event is not None
    assert isinstance(event, CalendarEvent)
    assert event.summary == "Mathematics"


@pytest.mark.asyncio
async def test_calendar_no_events(mock_coordinator, mock_config_entry):
    """Test calendar with no events."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Clear events
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"] = []

    event = calendar.event
    assert event is None


@pytest.mark.asyncio
async def test_calendar_get_events(mock_coordinator, mock_config_entry):
    """Test calendar get_events method."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    now = dt_util.now()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=7)

    events = await calendar.async_get_events(None, start_date, end_date)

    assert len(events) == 2
    assert all(isinstance(event, CalendarEvent) for event in events)
    assert events[0].summary == "Mathematics"
    assert events[1].summary == "Science"


@pytest.mark.asyncio
async def test_calendar_get_events_filtered_by_date(mock_coordinator, mock_config_entry):
    """Test calendar get_events with date filtering."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    now = dt_util.now()
    # Only request today's events
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    # Mock first event to be today, second to be tomorrow
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]["start"] = now.replace(hour=9)
    mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]["end"] = now.replace(hour=10)
    
    events = await calendar.async_get_events(None, start_date, end_date)

    # Should only return today's event
    assert len(events) == 1
    assert events[0].summary == "Mathematics"


@pytest.mark.asyncio
async def test_calendar_convert_event_with_description(mock_coordinator, mock_config_entry):
    """Test calendar event conversion with full event data."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Get first event from coordinator data
    event_data = mock_coordinator.data["children_data"]["test-child-123"]["events"]["week"][0]
    
    calendar_event = calendar._convert_to_calendar_event(event_data)

    assert isinstance(calendar_event, CalendarEvent)
    assert calendar_event.summary == "Mathematics"
    assert calendar_event.location == "Room 101"
    assert "Algebra lesson" in calendar_event.description
    assert "Class: Year 10" in calendar_event.description
    assert "Attendees: Mr. Smith" in calendar_event.description


@pytest.mark.asyncio
async def test_calendar_device_info(mock_coordinator, mock_config_entry):
    """Test calendar device info."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    device_info = calendar.device_info
    assert device_info is not None
    assert device_info.get("identifiers") == {(DOMAIN, mock_config_entry.entry_id)}
    assert "Firefly Cloud" in str(device_info.get("name", ""))
    assert device_info.get("manufacturer") == "Firefly Learning"
    assert device_info.get("model") == "Firefly Cloud Integration"


@pytest.mark.asyncio
async def test_calendar_name_includes_child_name(mock_config_entry):
    """Test calendar name includes child name when available."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "children_data": {
            "child-123": {
                "name": "John Doe",
                "events": {"week": []},
                "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
            }
        }
    }

    calendar = FireflyCalendar(coordinator, mock_config_entry, "child-123")

    assert "John Doe" in calendar.name
    assert "Schedule" in calendar.name


@pytest.mark.asyncio
async def test_calendar_name_fallback_to_guid(mock_config_entry):
    """Test calendar name falls back to GUID when no name available."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "children_data": {
            "child-123": {
                "events": {"week": []},
                "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
            }
        }
    }

    calendar = FireflyCalendar(coordinator, mock_config_entry, "child-123")

    assert "child-12" in calendar.name  # First 8 chars of "child-123"
    assert "Schedule" in calendar.name


@pytest.mark.asyncio
async def test_calendar_multiple_children_setup(hass: HomeAssistant):
    """Test calendar setup with multiple children."""
    # Create config entry with 2 children
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
            CONF_CHILDREN_GUIDS: ["child-1", "child-2"],
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
        "children_guids": ["child-1", "child-2"],
        "children_data": {
            "child-1": {
                "name": "Child One",
                "events": {"week": []},
                "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
            },
            "child-2": {
                "name": "Child Two",
                "events": {"week": []},
                "tasks": {"upcoming": [], "due_today": [], "all": [], "overdue": []},
            },
        },
    }

    hass.data[DOMAIN] = {config_entry.entry_id: coordinator}

    entities = []

    def mock_add_entities(new_entities, update_before_add=False):  # pylint: disable=unused-argument
        entities.extend(new_entities)

    await async_setup_entry(hass, config_entry, mock_add_entities)

    # Should create 2 calendar entities (one per child)
    assert len(entities) == 2

    # Check all children have calendar entities
    child_guids = [e._child_guid for e in entities]
    assert "child-1" in child_guids
    assert "child-2" in child_guids


@pytest.mark.asyncio
async def test_calendar_event_build_description_empty_fields(mock_coordinator, mock_config_entry):
    """Test calendar event description building with empty optional fields."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Event with minimal data
    event_data = {
        "start": dt_util.now(),
        "end": dt_util.now() + timedelta(hours=1),
        "subject": "Test Subject",
        "location": "Test Location",
        "description": None,
        "guild": None,
        "attendees": [],
    }

    calendar_event = calendar._convert_to_calendar_event(event_data)

    assert calendar_event.summary == "Test Subject"
    assert calendar_event.location == "Test Location"
    # Description should be None when no meaningful data to include
    assert calendar_event.description is None


@pytest.mark.asyncio
async def test_calendar_event_build_description_with_many_attendees(mock_coordinator, mock_config_entry):
    """Test calendar event description with many attendees (truncation)."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Event with many attendees
    event_data = {
        "start": dt_util.now(),
        "end": dt_util.now() + timedelta(hours=1),
        "subject": "Test Subject",
        "location": "Test Location",
        "description": "Test description",
        "guild": "Year 10",
        "attendees": [f"Teacher {i}" for i in range(10)],  # 10 attendees
    }

    calendar_event = calendar._convert_to_calendar_event(event_data)

    assert "Test description" in calendar_event.description
    assert "Class: Year 10" in calendar_event.description
    assert "and 5 more" in calendar_event.description  # Should truncate after first 5


@pytest.mark.asyncio
async def test_calendar_no_coordinator_data(mock_config_entry):
    """Test calendar with no coordinator data."""
    coordinator = MagicMock()
    coordinator.data = None
    coordinator.last_update_success = False

    calendar = FireflyCalendar(coordinator, mock_config_entry, "test-child-123")

    assert calendar.available is False
    assert calendar.event is None

    # Should handle get_events gracefully
    events = await calendar.async_get_events(None, dt_util.now(), dt_util.now() + timedelta(days=1))
    assert events == []


@pytest.mark.asyncio
async def test_calendar_get_events_no_data(mock_config_entry):
    """Test calendar get_events with no coordinator data."""
    coordinator = MagicMock()
    coordinator.data = None

    calendar = FireflyCalendar(coordinator, mock_config_entry, "test-child-123")

    now = dt_util.now()
    events = await calendar.async_get_events(None, now, now + timedelta(days=1))

    assert events == []


@pytest.mark.asyncio
async def test_calendar_handles_missing_child_data_gracefully(mock_config_entry):
    """Test calendar handles missing child data gracefully."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = {
        "user_info": {"username": "test", "fullname": "Test User", "guid": "test-123"},
        "children_data": {},  # Missing the specific child
    }

    calendar = FireflyCalendar(coordinator, mock_config_entry, "missing-child-123")

    # Should not crash and return sensible defaults
    assert calendar.available is False
    assert calendar.event is None

    # get_events should return empty list
    now = dt_util.now()
    events = await calendar.async_get_events(None, now, now + timedelta(days=1))
    assert events == []