"""Test the Firefly Cloud calendar platform."""

from datetime import timedelta
from types import MappingProxyType
from unittest.mock import MagicMock

import pytest
from conftest import create_config_entry_with_version_compat, make_child, make_data, make_lesson
from homeassistant.components.calendar import CalendarEvent
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from custom_components.firefly_cloud.calendar import FireflyCalendar, async_setup_entry
from custom_components.firefly_cloud.const import (
    CONF_CHILDREN_GUIDS,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_SCHOOL_NAME,
    CONF_SECRET,
    CONF_USER_GUID,
    DOMAIN,
)
from custom_components.firefly_cloud.models import Lesson


def _lesson(start, end, subject, location, description, guild, attendees):
    """Build a Lesson with every field set."""
    return Lesson(
        start=start,
        end=end,
        subject=subject,
        location=location,
        description=description,
        guild=guild,
        attendees=tuple(attendees),
    )


def _set_lessons(coordinator, *lessons, guid="test-child-123"):
    """Replace a child's lessons in the coordinator data."""
    coordinator.data = make_data(
        make_child(guid, lessons=lessons, today=dt_util.now().date(), name="John Doe"),
        make_child("test-child-456", today=dt_util.now().date(), name="Jane Doe"),
    )


def _maths(start, end):
    """Build the first fixture lesson at a different time."""
    return _lesson(start, end, "Mathematics", "Room 101", "Algebra lesson", "Year 10", ["Mr. Smith"])


def _science(now):
    """Build the second fixture lesson (tomorrow 11:00)."""
    return _lesson(
        now.replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1),
        now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1),
        "Science",
        "Lab 1",
        "Chemistry experiment",
        "Year 10",
        ["Ms. Johnson"],
    )


@pytest.fixture
def mock_coordinator():
    """Return a mock coordinator with calendar data."""
    coordinator = MagicMock()
    now = dt_util.now()

    _set_lessons(
        coordinator,
        _lesson(
            now.replace(hour=9, minute=0, second=0, microsecond=0),
            now.replace(hour=10, minute=0, second=0, microsecond=0),
            "Mathematics",
            "Room 101",
            "Algebra lesson",
            "Year 10",
            ["Mr. Smith"],
        ),
        _lesson(
            now.replace(hour=11, minute=0, second=0, microsecond=0) + timedelta(days=1),
            now.replace(hour=12, minute=0, second=0, microsecond=0) + timedelta(days=1),
            "Science",
            "Lab 1",
            "Chemistry experiment",
            "Year 10",
            ["Ms. Johnson"],
        ),
    )

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
    mock_coordinator.data = make_data(make_child("test-child-123", today=dt_util.now().date()))
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
    _set_lessons(mock_coordinator, _maths(now - timedelta(minutes=30), now + timedelta(minutes=30)), _science(now))

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
    _set_lessons(mock_coordinator, _maths(now + timedelta(hours=1), now + timedelta(hours=2)), _science(now))

    event = calendar.event
    assert event is not None
    assert isinstance(event, CalendarEvent)
    assert event.summary == "Mathematics"


@pytest.mark.asyncio
async def test_calendar_no_events(mock_coordinator, mock_config_entry):
    """Test calendar with no events."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Clear events
    _set_lessons(mock_coordinator)

    event = calendar.event
    assert event is None


@pytest.mark.asyncio
async def test_calendar_get_events(hass, mock_coordinator, mock_config_entry):
    """Test calendar get_events method."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    now = dt_util.now()
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=7)

    events = await calendar.async_get_events(hass, start_date, end_date)

    assert len(events) == 2
    assert all(isinstance(event, CalendarEvent) for event in events)
    assert events[0].summary == "Mathematics"
    assert events[1].summary == "Science"


@pytest.mark.asyncio
async def test_calendar_get_events_filtered_by_date(hass, mock_coordinator, mock_config_entry):
    """Test calendar get_events with date filtering."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    now = dt_util.now()
    # Only request today's events
    start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end_date = start_date + timedelta(days=1)

    # Mock first event to be today, second to be tomorrow
    _set_lessons(mock_coordinator, _maths(now.replace(hour=9), now.replace(hour=10)), _science(now))
    events = await calendar.async_get_events(hass, start_date, end_date)

    # Should only return today's event
    assert len(events) == 1
    assert events[0].summary == "Mathematics"


@pytest.mark.asyncio
async def test_calendar_convert_event_with_description(mock_coordinator, mock_config_entry):
    """Test calendar event conversion with full event data."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Get first event from coordinator data
    event_data = mock_coordinator.data.child("test-child-123").lessons[0]
    calendar_event = calendar._convert_to_calendar_event(event_data)

    assert isinstance(calendar_event, CalendarEvent)
    assert calendar_event.summary == "Mathematics"
    assert calendar_event.location == "Room 101"
    assert calendar_event.description and "Algebra lesson" in calendar_event.description
    assert calendar_event.description and "Class: Year 10" in calendar_event.description
    assert calendar_event.description and "Attendees: Mr. Smith" in calendar_event.description


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
    coordinator.data = make_data(make_child("child-123", today=dt_util.now().date(), name="John Doe"))

    calendar = FireflyCalendar(coordinator, mock_config_entry, "child-123")

    assert "John Doe" in calendar.name
    assert "Schedule" in calendar.name


@pytest.mark.asyncio
async def test_calendar_name_fallback_to_guid(mock_config_entry):
    """Test calendar name falls back to GUID when no name available."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = make_data(make_child("child-123", today=dt_util.now().date(), name=None))

    calendar = FireflyCalendar(coordinator, mock_config_entry, "child-123")

    assert "child-12" in calendar.name  # First 8 chars of "child-123"
    assert "Schedule" in calendar.name


@pytest.mark.asyncio
async def test_calendar_multiple_children_setup(hass: HomeAssistant):
    """Test calendar setup with multiple children."""
    # Create config entry with 2 children
    config_entry = create_config_entry_with_version_compat(
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
    )

    coordinator = MagicMock()
    today = dt_util.now().date()
    coordinator.data = make_data(
        make_child("child-1", today=today, name="Child One"),
        make_child("child-2", today=today, name="Child Two"),
        user_info={"username": "parent", "fullname": "Parent User"},
    )

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
    event_data = make_lesson(dt_util.now(), subject="Test Subject", location="Test Location", description=None)

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
    event_data = make_lesson(
        dt_util.now(),
        subject="Test Subject",
        location="Test Location",
        description="Test description",
        guild="Year 10",
        attendees=[f"Teacher {i}" for i in range(10)],
    )

    calendar_event = calendar._convert_to_calendar_event(event_data)

    assert calendar_event.description and "Test description" in calendar_event.description
    assert calendar_event.description and "Class: Year 10" in calendar_event.description
    assert calendar_event.description and "and 5 more" in calendar_event.description  # Should truncate after first 5


@pytest.mark.asyncio
async def test_calendar_event_build_description_with_dict_attendees(mock_coordinator, mock_config_entry):
    """Test calendar event description with dictionary attendees (real API format)."""
    calendar = FireflyCalendar(mock_coordinator, mock_config_entry, "test-child-123")

    # Event with dictionary attendees (how they come from the real API)
    event_data = make_lesson(
        dt_util.now(),
        subject="Chemistry Lab",
        location="Science Lab 1",
        description="Bring safety goggles",
        guild="Year 11",
        attendees=[
            {"name": "Dr. Smith", "role": "teacher"},
            {"name": "Ms. Johnson", "role": "assistant"},
            {"name": "Mr. Brown"},  # Missing role
        ],
    )

    calendar_event = calendar._convert_to_calendar_event(event_data)

    assert calendar_event.summary == "Chemistry Lab"
    assert calendar_event.location == "Science Lab 1"
    assert calendar_event.description and "Bring safety goggles" in calendar_event.description
    assert calendar_event.description and "Class: Year 11" in calendar_event.description
    assert calendar_event.description and "Attendees: Dr. Smith, Ms. Johnson, Mr. Brown" in calendar_event.description


@pytest.mark.asyncio
async def test_calendar_no_coordinator_data(hass, mock_config_entry):
    """Test calendar with no coordinator data."""
    coordinator = MagicMock()
    coordinator.data = None
    coordinator.last_update_success = False

    calendar = FireflyCalendar(coordinator, mock_config_entry, "test-child-123")

    assert calendar.available is False
    assert calendar.event is None

    # Should handle get_events gracefully
    events = await calendar.async_get_events(hass, dt_util.now(), dt_util.now() + timedelta(days=1))
    assert events == []


@pytest.mark.asyncio
async def test_calendar_get_events_no_data(hass, mock_config_entry):
    """Test calendar get_events with no coordinator data."""
    coordinator = MagicMock()
    coordinator.data = None

    calendar = FireflyCalendar(coordinator, mock_config_entry, "test-child-123")

    now = dt_util.now()
    events = await calendar.async_get_events(hass, now, now + timedelta(days=1))

    assert events == []


@pytest.mark.asyncio
async def test_calendar_handles_missing_child_data_gracefully(hass, mock_config_entry):
    """Test calendar handles missing child data gracefully."""
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = make_data(user_info={"username": "test", "fullname": "Test User", "guid": "test-123"})

    calendar = FireflyCalendar(coordinator, mock_config_entry, "missing-child-123")

    # Should not crash and return sensible defaults
    assert calendar.available is False
    assert calendar.event is None

    # get_events should return empty list
    now = dt_util.now()
    events = await calendar.async_get_events(hass, now, now + timedelta(days=1))
    assert events == []


@pytest.mark.asyncio
async def test_calendar_handles_lessons_without_timezone(hass, mock_config_entry):
    """A lesson Firefly sent with no timezone is made timezone-aware, so the calendar can compare it."""
    now = dt_util.now()
    naive_start = (now - timedelta(minutes=30)).replace(tzinfo=None)
    naive_end = (now + timedelta(minutes=30)).replace(tzinfo=None)
    lesson = Lesson.from_firefly(
        {
            "start": naive_start.isoformat(),
            "end": naive_end.isoformat(),
            "subject": "Maths",
            "location": "M8",
        }
    )
    coordinator = MagicMock()
    coordinator.last_update_success = True
    coordinator.data = make_data(make_child("test-child-123", lessons=[lesson], today=now.date()))
    calendar = FireflyCalendar(coordinator, mock_config_entry, "test-child-123")

    event = calendar.event
    events = await calendar.async_get_events(hass, now - timedelta(days=1), now + timedelta(days=1))

    assert event is not None
    assert event.summary == "Maths"
    assert [e.summary for e in events] == ["Maths"]


@pytest.mark.asyncio
async def test_calendar_get_events_child_without_lessons(hass, mock_config_entry):
    """A child with no lessons has no calendar events."""
    coordinator = MagicMock()
    coordinator.data = make_data(make_child("test-child-123", today=dt_util.now().date()))

    calendar = FireflyCalendar(coordinator, mock_config_entry, "test-child-123")

    now = dt_util.now()
    events = await calendar.async_get_events(hass, now, now + timedelta(days=7))

    assert events == []


@pytest.mark.asyncio
async def test_calendar_current_event_with_multiple_overlapping(hass, mock_config_entry):
    """Test calendar current event selection with multiple overlapping events."""
    now = dt_util.now()

    coordinator = MagicMock()
    coordinator.data = make_data(
        make_child(
            "test-child-123",
            lessons=[
                _lesson(
                    now - timedelta(minutes=30),
                    now + timedelta(minutes=30),
                    "Math Class",
                    "Room 101",
                    "First class",
                    None,
                    [],
                ),
                _lesson(
                    now - timedelta(minutes=15),
                    now + timedelta(minutes=45),
                    "Study Hall",
                    "Library",
                    "Second class",
                    None,
                    [],
                ),
            ],
            today=now.date(),
        )
    )
    coordinator.last_update_success = True

    calendar = FireflyCalendar(coordinator, mock_config_entry, "test-child-123")

    # Should return the first overlapping event
    current_event = calendar.event
    assert current_event is not None
    assert current_event.summary == "Math Class"


@pytest.mark.asyncio
async def test_calendar_build_description_none_values(hass, mock_config_entry):
    """Test calendar build_description with None values."""
    coordinator = MagicMock()
    calendar = FireflyCalendar(coordinator, mock_config_entry, "test-child-123")

    event_data = make_lesson(dt_util.now(), description=None)

    description = calendar._build_event_description(event_data)

    # Should handle None values gracefully and return None when no description parts exist
    assert description is None


@pytest.mark.asyncio
async def test_calendar_listens_to_coordinator_once(hass, mock_coordinator, mock_config_entry):
    """CoordinatorEntity's own subscription is the only one, so each update writes state once."""
    calendar = FireflyCalendar(
        coordinator=mock_coordinator, config_entry=mock_config_entry, child_guid="test-child-123"
    )
    mock_coordinator.async_add_listener = MagicMock(return_value=MagicMock())

    await calendar.async_added_to_hass()

    mock_coordinator.async_add_listener.assert_called_once()
