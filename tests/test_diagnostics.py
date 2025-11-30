"""Test the Firefly Cloud diagnostics."""

from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
from homeassistant.core import HomeAssistant

from custom_components.firefly_cloud.const import (
    CONF_CHILDREN_GUIDS,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_SCHOOL_CODE,
    CONF_SCHOOL_NAME,
    CONF_SECRET,
    CONF_TASK_LOOKAHEAD_DAYS,
    CONF_USER_GUID,
    DOMAIN,
)
from custom_components.firefly_cloud.coordinator import FireflyUpdateCoordinator
from custom_components.firefly_cloud.diagnostics import async_get_config_entry_diagnostics
from tests.conftest import create_config_entry_with_version_compat


@pytest.fixture
def mock_coordinator(hass):
    """Return a mock coordinator with test data."""
    api = AsyncMock()
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=api,
        task_lookahead_days=7,
    )

    # Set up test data
    coordinator.data = {
        "user_info": {"guid": "test-user-123", "username": "test_user"},
        "children_guids": ["child-1", "child-2"],
        "children_data": {},
        "last_updated": datetime.now(timezone.utc),
    }

    # Set up statistics
    coordinator.statistics = {
        "total_updates": 10,
        "successful_updates": 8,
        "failed_updates": 2,
        "last_update_time": "2024-01-01T12:00:00+00:00",
        "last_success_time": "2024-01-01T12:00:00+00:00",
        "last_failure_time": "2024-01-01T11:00:00+00:00",
        "error_counts": {"FireflyConnectionError": 2},
    }

    coordinator.last_update_success = True

    return coordinator


@pytest.mark.asyncio
async def test_diagnostics_basic_structure(hass: HomeAssistant, mock_coordinator):
    """Test basic diagnostics structure."""
    from types import MappingProxyType

    entry = create_config_entry_with_version_compat(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "testschool.fireflysolutions.co.uk",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "secret-token-456",
            CONF_USER_GUID: "user-guid-789",
            CONF_CHILDREN_GUIDS: ["child-1", "child-2"],
        },
        options={},
        entry_id="test-entry-1",
        unique_id="test-unique-1",
        source="user",
        discovery_keys=MappingProxyType({}),
    )

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert "entry" in diagnostics
    assert "coordinator" in diagnostics
    assert "data_summary" in diagnostics


@pytest.mark.asyncio
async def test_diagnostics_entry_data(hass: HomeAssistant, mock_coordinator):
    """Test that entry data is properly included and redacted."""
    from types import MappingProxyType

    entry = create_config_entry_with_version_compat(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "testschool.fireflysolutions.co.uk",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "secret-token-456",
            CONF_USER_GUID: "user-guid-789",
            CONF_CHILDREN_GUIDS: ["child-1", "child-2"],
        },
        options={},
        entry_id="test-entry-2",
        unique_id="test-unique-2",
        source="user",
        discovery_keys=MappingProxyType({}),
    )

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    entry_data = diagnostics["entry"]
    assert entry_data["title"] == "Test School"

    # Check sensitive data is redacted
    assert entry_data["data"][CONF_DEVICE_ID] == "**REDACTED**"
    assert entry_data["data"][CONF_SECRET] == "**REDACTED**"

    # Check non-sensitive data is included
    assert entry_data["data"][CONF_SCHOOL_CODE] == "testschool"
    assert entry_data["data"][CONF_SCHOOL_NAME] == "Test School"
    assert entry_data["data"][CONF_HOST] == "testschool.fireflysolutions.co.uk"
    assert entry_data["data"][CONF_USER_GUID] == "user-guid-789"
    assert entry_data["data"][CONF_CHILDREN_GUIDS] == ["child-1", "child-2"]


@pytest.mark.asyncio
async def test_diagnostics_coordinator_statistics(hass: HomeAssistant, mock_coordinator):
    """Test that coordinator statistics are included."""
    from types import MappingProxyType

    entry = create_config_entry_with_version_compat(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "testschool.fireflysolutions.co.uk",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "secret-token-456",
            CONF_USER_GUID: "user-guid-789",
        },
        options={},
        entry_id="test-entry-3",
        unique_id="test-unique-3",
        source="user",
        discovery_keys=MappingProxyType({}),
    )

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    coordinator_data = diagnostics["coordinator"]
    assert coordinator_data["last_update_success"] is True
    assert "statistics" in coordinator_data

    stats = coordinator_data["statistics"]
    assert stats["total_updates"] == 10
    assert stats["successful_updates"] == 8
    assert stats["failed_updates"] == 2
    assert stats["last_update_time"] == "2024-01-01T12:00:00+00:00"
    assert stats["error_counts"]["FireflyConnectionError"] == 2


@pytest.mark.asyncio
async def test_diagnostics_data_summary(hass: HomeAssistant, mock_coordinator):
    """Test that data summary is properly generated."""
    from types import MappingProxyType

    entry = create_config_entry_with_version_compat(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "testschool.fireflysolutions.co.uk",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "secret-token-456",
            CONF_USER_GUID: "user-guid-789",
            CONF_CHILDREN_GUIDS: ["child-1", "child-2"],
        },
        options={},
        entry_id="test-entry-4",
        unique_id="test-unique-4",
        source="user",
        discovery_keys=MappingProxyType({}),
    )

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    data_summary = diagnostics["data_summary"]
    assert data_summary["children_count"] == 2
    assert data_summary["has_user_info"] is True
    assert data_summary["last_updated"] is not None


@pytest.mark.asyncio
async def test_diagnostics_with_options(hass: HomeAssistant, mock_coordinator):
    """Test diagnostics with entry options."""
    from types import MappingProxyType

    entry = create_config_entry_with_version_compat(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "testschool.fireflysolutions.co.uk",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "secret-token-456",
            CONF_USER_GUID: "user-guid-789",
        },
        options={
            CONF_TASK_LOOKAHEAD_DAYS: 14,
        },
        entry_id="test-entry-5",
        unique_id="test-unique-5",
        source="user",
        discovery_keys=MappingProxyType({}),
    )

    hass.data[DOMAIN] = {entry.entry_id: mock_coordinator}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    entry_data = diagnostics["entry"]
    assert entry_data["options"][CONF_TASK_LOOKAHEAD_DAYS] == 14


@pytest.mark.asyncio
async def test_diagnostics_no_coordinator_data(hass: HomeAssistant):
    """Test diagnostics when coordinator has no data."""
    from types import MappingProxyType

    api = AsyncMock()
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=api,
        task_lookahead_days=7,
    )
    coordinator.data = None

    entry = create_config_entry_with_version_compat(
        version=1,
        minor_version=1,
        domain=DOMAIN,
        title="Test School",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "testschool.fireflysolutions.co.uk",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "secret-token-456",
            CONF_USER_GUID: "user-guid-789",
        },
        options={},
        entry_id="test-entry-6",
        unique_id="test-unique-6",
        source="user",
        discovery_keys=MappingProxyType({}),
    )

    hass.data[DOMAIN] = {entry.entry_id: coordinator}

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    data_summary = diagnostics["data_summary"]
    assert data_summary["children_count"] == 0
    assert data_summary["has_user_info"] is False
    assert data_summary["last_updated"] is None
