"""Test configuration for Firefly Cloud integration."""
import json
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

import pytest
import pytest_asyncio
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME

# Import Home Assistant test utilities
try:
    from homeassistant.testing import get_fixture_path
except ImportError:
    pass

# Configure pytest for Home Assistant testing
@pytest.fixture
async def hass():
    """Return a Home Assistant instance for testing."""
    from homeassistant.core import HomeAssistant
    from homeassistant.config import Config
    
    hass = HomeAssistant()
    hass.config = Config(hass)
    hass.data = {}
    return hass

from custom_components.firefly_cloud.const import (
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


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Return a mock config entry."""
    return ConfigEntry(
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
            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
        },
        options={},
        entry_id="test-entry-id",
    )


@pytest.fixture
def mock_school_info():
    """Return mock school info."""
    return {
        "enabled": True,
        "name": "Test School",
        "id": "test-installation-id",
        "host": "testschool.fireflycloud.net",
        "ssl": True,
        "url": "https://testschool.fireflycloud.net",
        "token_url": "https://testschool.fireflycloud.net/login/login.aspx?prelogin=...",
        "device_id": "test-device-123",
    }


@pytest.fixture
def mock_user_info():
    """Return mock user info."""
    return {
        "username": "john.doe",
        "fullname": "John Doe",
        "email": "john.doe@test.com",
        "role": "student",
        "guid": "test-user-789",
    }


@pytest.fixture
def mock_events():
    """Return mock event data."""
    now = datetime.now()
    today = now.replace(hour=9, minute=0, second=0, microsecond=0)
    
    return [
        {
            "start": today.isoformat() + "Z",
            "end": (today + timedelta(hours=1)).isoformat() + "Z",
            "subject": "Mathematics",
            "location": "Room 101",
            "description": "Algebra lesson",
            "guild": None,
            "attendees": [],
        },
        {
            "start": (today + timedelta(hours=1)).isoformat() + "Z",
            "end": (today + timedelta(hours=2)).isoformat() + "Z",
            "subject": "English Literature",
            "location": "Room 201",
            "description": "Shakespeare analysis",
            "guild": None,
            "attendees": [],
        },
        {
            "start": (today + timedelta(hours=2)).isoformat() + "Z",
            "end": (today + timedelta(hours=3)).isoformat() + "Z",
            "subject": "Physical Education",
            "location": "Gymnasium",
            "description": "Sports kit required",
            "guild": None,
            "attendees": [],
        },
    ]


@pytest.fixture
def mock_tasks():
    """Return mock task data."""
    now = datetime.now()
    tomorrow = now + timedelta(days=1)
    next_week = now + timedelta(days=7)
    
    return [
        {
            "guid": "task-1",
            "title": "Math Homework - Chapter 5",
            "description": "Complete exercises 1-20 from Chapter 5",
            "dueDate": tomorrow.isoformat() + "Z",
            "setDate": (now - timedelta(days=1)).isoformat() + "Z",
            "subject": {"name": "Mathematics"},
            "completionStatus": "Todo",
            "setter": {"name": "Mr. Smith"},
        },
        {
            "guid": "task-2",
            "title": "History Essay - World War II",
            "description": "Write a 1000-word essay on WWII causes",
            "dueDate": next_week.isoformat() + "Z",
            "setDate": (now - timedelta(days=3)).isoformat() + "Z",
            "subject": {"name": "History"},
            "completionStatus": "Todo",
            "setter": {"name": "Mrs. Johnson"},
        },
        {
            "guid": "task-3",
            "title": "Science Test Preparation",
            "description": "Study for chemistry test",
            "dueDate": (now + timedelta(days=3)).isoformat() + "Z",
            "setDate": now.isoformat() + "Z",
            "subject": {"name": "Science"},
            "completionStatus": "Todo",
            "setter": {"name": "Dr. Brown"},
        },
    ]


@pytest.fixture
def mock_api_responses(mock_events, mock_tasks):
    """Return mock API responses."""
    return {
        "events": mock_events,
        "tasks": {"items": mock_tasks},
        "version": {
            "majorVersion": 1,
            "minorVersion": 0,
            "incrementVersion": 0,
        },
        "verify_token": {"valid": True},
    }


@pytest.fixture
def mock_firefly_api():
    """Return a mock Firefly API client."""
    api = AsyncMock()
    api.verify_credentials.return_value = True
    api.get_api_version.return_value = {"major": 1, "minor": 0, "increment": 0}
    api.get_user_info.return_value = {
        "username": "john.doe",
        "fullname": "John Doe",
        "email": "john.doe@test.com",
        "role": "student",
        "guid": "test-user-789",
    }
    return api


@pytest.fixture
def mock_coordinator_data():
    """Return mock coordinator data."""
    now = datetime.now()
    today_events = [
        {
            "start": now.replace(hour=9, minute=0, second=0, microsecond=0),
            "end": now.replace(hour=10, minute=0, second=0, microsecond=0),
            "subject": "Mathematics",
            "location": "Room 101",
            "description": "Algebra lesson",
            "guild": None,
            "attendees": [],
        }
    ]
    
    upcoming_tasks = [
        {
            "id": "task-1",
            "title": "Math Homework",
            "description": "Complete exercises",
            "due_date": now + timedelta(days=1),
            "set_date": now - timedelta(days=1),
            "subject": "Mathematics",
            "task_type": "homework",
            "completion_status": "Todo",
            "setter": "Mr. Smith",
            "raw_data": {},
        }
    ]
    
    return {
        "user_info": {
            "username": "john.doe",
            "fullname": "John Doe",
            "email": "john.doe@test.com",
            "role": "student",
            "guid": "test-user-789",
        },
        "events": {
            "today": today_events,
            "week": today_events,
        },
        "tasks": {
            "all": upcoming_tasks,
            "due_today": [],
            "upcoming": upcoming_tasks,
            "overdue": [],
        },
        "last_updated": now,
    }


@pytest.fixture
def mock_aiohttp_session():
    """Return a mock aiohttp session."""
    session = AsyncMock()
    
    # Configure the context manager behavior
    response = AsyncMock()
    session.get.return_value.__aenter__.return_value = response
    session.post.return_value.__aenter__.return_value = response
    
    return session