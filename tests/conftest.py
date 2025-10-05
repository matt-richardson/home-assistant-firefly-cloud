"""Test configuration for Firefly Cloud integration."""

import inspect
from datetime import datetime, timedelta
from types import MappingProxyType
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from homeassistant.config_entries import ConfigEntry

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


def create_config_entry_with_version_compat(**kwargs):
    """Create a ConfigEntry with version-compatible parameters.

    Home Assistant 2025.x requires 'subentries_data' parameter,
    while older versions don't accept it.
    """
    # Check if ConfigEntry.__init__ accepts subentries_data parameter
    sig = inspect.signature(ConfigEntry.__init__)
    params = sig.parameters

    if "subentries_data" in params:
        # HA 2025.x and newer - subentries_data is required
        if "subentries_data" not in kwargs:
            kwargs["subentries_data"] = {}
    else:
        # Older HA versions - subentries_data doesn't exist
        kwargs.pop("subentries_data", None)

    return ConfigEntry(**kwargs)


# Configure pytest for Home Assistant testing
@pytest_asyncio.fixture
async def hass():
    """Return a Home Assistant instance for testing."""
    import tempfile

    from homeassistant.config_entries import ConfigEntries
    from homeassistant.core import HomeAssistant

    with tempfile.TemporaryDirectory() as temp_dir:
        hass = HomeAssistant(temp_dir)
        # Use proper initialization instead of direct assignment
        hass.config_entries = ConfigEntries(hass, {})

        # Set up required components for config flow testing
        hass.data["components"] = set()
        hass.data["setup_started"] = set()
        hass.data["preload_platforms"] = set()
        hass.data["registries_loaded"] = set()
        hass.data["missing_platforms"] = {}
        hass.data["integrations"] = {}

        # Add network component data to prevent KeyError
        # Mock the network component structure that Home Assistant expects
        from unittest.mock import MagicMock

        network_adapter = MagicMock()
        network_adapter.adapters = []
        hass.data["network"] = network_adapter

        # Mock the integration registry and loader
        mock_integration = AsyncMock()
        mock_integration.domain = "firefly_cloud"
        mock_integration.name = "Firefly Cloud"
        mock_integration.dependencies = set()
        mock_integration.requirements = []
        mock_integration.config_flow = True
        mock_integration.file_path = temp_dir + "/custom_components/firefly_cloud"

        # Setup required Home Assistant components and register config flow
        with patch("homeassistant.loader.async_get_integration", return_value=mock_integration):
            with patch("homeassistant.helpers.integration_platform.async_process_integration_platforms"):
                with patch("homeassistant.helpers.frame.report_usage"):
                    # Import and register the config flow handler manually
                    from homeassistant.config_entries import HANDLERS

                    from custom_components.firefly_cloud.config_flow import FireflyCloudConfigFlow

                    HANDLERS["firefly_cloud"] = FireflyCloudConfigFlow

                    await hass.async_start()
                    try:
                        yield hass
                    finally:
                        await hass.async_stop()


@pytest.fixture
def mock_config_entry() -> ConfigEntry:
    """Return a mock config entry."""
    return create_config_entry_with_version_compat(
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
        options={},
        entry_id="test-entry-id",
        unique_id="test-unique-id",
        source="user",
        discovery_keys=MappingProxyType({}),
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
    api.get_children_info.return_value = [
        {
            "username": "child1",
            "fullname": "Child One",
            "email": "child1@test.com",
            "role": "student",
            "guid": "test-child-123",
        },
        {
            "username": "child2",
            "fullname": "Child Two",
            "email": "child2@test.com",
            "role": "student",
            "guid": "test-child-456",
        },
    ]
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
        "children_guids": ["test-child-123", "test-child-456"],
        "children_data": {
            "test-child-123": {
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
            },
            "test-child-456": {
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
        "last_updated": now,
    }


def mock_http_response(text="", json_data=None, status=200, raise_for_status_exception=None):
    """Create a mock HTTP response."""
    response = AsyncMock()
    response.text = AsyncMock(return_value=text)
    if json_data:
        response.json = AsyncMock(return_value=json_data)
    response.status = status

    if raise_for_status_exception:
        response.raise_for_status = MagicMock(side_effect=raise_for_status_exception)
    else:
        response.raise_for_status = MagicMock()
    return response


@pytest.fixture
def mock_aiohttp_session():
    """Return a mock aiohttp session."""
    session = MagicMock()

    # Store for configuring responses per test
    session._mock_responses = {}

    # Create async context manager mocks that return configured responses
    def create_context_manager_for_get(*_args, **_kwargs):  # pylint: disable=unused-argument
        context_manager = AsyncMock()
        # Use the stored response or create a default one
        response = session._mock_responses.get("get", mock_http_response())
        context_manager.__aenter__.return_value = response
        context_manager.__aexit__.return_value = None
        return context_manager

    def create_context_manager_for_post(*_args, **_kwargs):  # pylint: disable=unused-argument
        context_manager = AsyncMock()
        # Use the stored response or create a default one
        response = session._mock_responses.get("post", mock_http_response())
        context_manager.__aenter__.return_value = response
        context_manager.__aexit__.return_value = None
        return context_manager

    session.get = MagicMock(side_effect=create_context_manager_for_get)
    session.post = MagicMock(side_effect=create_context_manager_for_post)

    return session
