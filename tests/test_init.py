"""Test the Firefly Cloud init module."""

from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady

from custom_components.firefly_cloud import (
    async_reload_entry,
    async_setup_entry,
    async_unload_entry,
    async_update_options,
)
from custom_components.firefly_cloud.const import (
    CONF_CHILDREN_GUIDS,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_SCHOOL_CODE,
    CONF_SCHOOL_NAME,
    CONF_SECRET,
    CONF_USER_GUID,
    DOMAIN,
)
from custom_components.firefly_cloud.exceptions import (
    FireflyAuthenticationError,
    FireflyConnectionError,
    FireflyTokenExpiredError,
)


@pytest.mark.asyncio
async def test_async_setup_entry_success(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_firefly_api: AsyncMock,
) -> None:
    """Test successful setup of config entry."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator") as mock_coordinator_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
        patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True),
    ):
        mock_api_class.return_value = mock_firefly_api
        mock_coordinator = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        # Test successful setup
        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]

        # Verify API client methods were called
        mock_firefly_api.verify_credentials.assert_called_once()
        mock_firefly_api.get_api_version.assert_called_once()

        # Verify coordinator was created and data fetched
        mock_coordinator.async_config_entry_first_refresh.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_auth_failed(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test setup with authentication failure."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
        patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True),
    ):
        mock_api = AsyncMock()
        mock_api.verify_credentials = AsyncMock(return_value=False)
        mock_api_class.return_value = mock_api

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_setup_entry_token_expired(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test setup with expired token."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
    ):
        mock_api = AsyncMock()
        mock_api.verify_credentials.side_effect = FireflyTokenExpiredError("Token expired")
        mock_api_class.return_value = mock_api

        with pytest.raises(ConfigEntryAuthFailed):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_setup_entry_connection_error(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test setup with connection error."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
    ):
        mock_api = AsyncMock()
        mock_api.verify_credentials.side_effect = FireflyConnectionError("Connection failed")
        mock_api_class.return_value = mock_api

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_setup_entry_coordinator_fetch_failure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_firefly_api: AsyncMock,
) -> None:
    """Test setup with coordinator data fetch failure."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator") as mock_coordinator_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
    ):
        mock_api_class.return_value = mock_firefly_api
        mock_coordinator = AsyncMock()
        mock_coordinator.async_config_entry_first_refresh.side_effect = Exception("Fetch failed")
        mock_coordinator_class.return_value = mock_coordinator

        with pytest.raises(ConfigEntryNotReady):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_unload_entry_success(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test successful unloading of config entry."""
    # Set up hass.data as if integration was loaded
    coordinator = AsyncMock()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = coordinator

    with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload_platforms:
        mock_unload_platforms.return_value = True

        result = await async_unload_entry(hass, mock_config_entry)

        assert result is True
        # Domain should be removed entirely since it was the only entry
        assert DOMAIN not in hass.data
        coordinator.async_shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_async_unload_entry_failure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test failed unloading of config entry."""
    # Set up hass.data as if integration was loaded
    coordinator = AsyncMock()
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = coordinator

    with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload_platforms:
        mock_unload_platforms.return_value = False

        result = await async_unload_entry(hass, mock_config_entry)

        assert result is False
        assert mock_config_entry.entry_id in hass.data[DOMAIN]
        coordinator.async_shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_async_reload_entry(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test reloading of config entry."""
    with (
        patch("custom_components.firefly_cloud.async_unload_entry") as mock_unload,
        patch("custom_components.firefly_cloud.async_setup_entry") as mock_setup,
    ):
        mock_unload.return_value = True
        mock_setup.return_value = True

        await async_reload_entry(hass, mock_config_entry)

        mock_unload.assert_called_once_with(hass, mock_config_entry)
        mock_setup.assert_called_once_with(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_update_options(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test updating of options."""
    with patch.object(hass.config_entries, "async_reload") as mock_reload:
        await async_update_options(hass, mock_config_entry)
        mock_reload.assert_called_once_with(mock_config_entry.entry_id)


@pytest.mark.asyncio
async def test_async_setup_entry_authentication_error(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test setup with authentication error."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
    ):
        mock_api = AsyncMock()
        mock_api.verify_credentials.side_effect = FireflyAuthenticationError("Auth failed")
        mock_api_class.return_value = mock_api

        with pytest.raises(ConfigEntryAuthFailed, match="Authentication failed"):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_setup_entry_unexpected_error(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test setup with unexpected error."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
    ):
        mock_api = AsyncMock()
        mock_api.verify_credentials.side_effect = ValueError("Unexpected error")
        mock_api_class.return_value = mock_api

        with pytest.raises(ConfigEntryNotReady, match="Unexpected error"):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_setup_entry_api_version_check_error(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_firefly_api: AsyncMock,
) -> None:
    """Test setup when API version check fails."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
    ):
        mock_api_class.return_value = mock_firefly_api
        mock_firefly_api.get_api_version.side_effect = FireflyConnectionError("Version check failed")

        with pytest.raises(ConfigEntryNotReady, match="Failed to connect"):
            await async_setup_entry(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_setup_entry_with_children_guids(
    hass: HomeAssistant,
    mock_firefly_api: AsyncMock,
) -> None:
    """Test setup with pre-configured children GUIDs."""
    from custom_components.firefly_cloud.const import CONF_CHILDREN_GUIDS

    # Create config entry with children GUIDs
    config_entry = Mock()
    config_entry.entry_id = "test-entry-id"
    config_entry.data = {
        "host": "https://testschool.fireflycloud.net",
        "device_id": "test-device-123",
        "secret": "test-secret-456",
        "user_guid": "test-user-789",
        CONF_CHILDREN_GUIDS: ["child-1", "child-2"],
        "task_lookahead_days": 7,
    }

    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator") as mock_coordinator_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
        patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True),
    ):
        mock_api_class.return_value = mock_firefly_api
        mock_coordinator = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        result = await async_setup_entry(hass, config_entry)

        assert result is True

        # Verify coordinator was created with children GUIDs
        mock_coordinator_class.assert_called_once()
        call_kwargs = mock_coordinator_class.call_args[1]
        assert call_kwargs["children_guids"] == ["child-1", "child-2"]


@pytest.mark.asyncio
async def test_async_setup_entry_forward_setup_failure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_firefly_api: AsyncMock,
) -> None:
    """Test setup when platform forward setup fails."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator") as mock_coordinator_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
        patch.object(hass.config_entries, "async_forward_entry_setups", return_value=False),
    ):
        mock_api_class.return_value = mock_firefly_api
        mock_coordinator = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        # Should still succeed even if forward setup fails (platforms might fail later)
        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id in hass.data[DOMAIN]


@pytest.mark.asyncio
async def test_async_unload_entry_multiple_entries(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test unloading when multiple config entries exist."""
    # Set up hass.data with multiple entries
    coordinator1 = AsyncMock()
    coordinator2 = AsyncMock()

    other_entry = Mock()
    other_entry.entry_id = "other-entry-id"

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = coordinator1
    hass.data[DOMAIN][other_entry.entry_id] = coordinator2

    with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload_platforms:
        mock_unload_platforms.return_value = True

        result = await async_unload_entry(hass, mock_config_entry)

        assert result is True
        # Only the specific entry should be removed, domain should remain
        assert DOMAIN in hass.data
        assert mock_config_entry.entry_id not in hass.data[DOMAIN]
        assert other_entry.entry_id in hass.data[DOMAIN]
        coordinator1.async_shutdown.assert_called_once()
        coordinator2.async_shutdown.assert_not_called()


@pytest.mark.asyncio
async def test_async_unload_entry_coordinator_shutdown_error(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test unloading when coordinator shutdown fails."""
    coordinator = AsyncMock()
    coordinator.async_shutdown.side_effect = Exception("Shutdown failed")

    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][mock_config_entry.entry_id] = coordinator

    with patch.object(hass.config_entries, "async_unload_platforms") as mock_unload_platforms:
        mock_unload_platforms.return_value = True

        # Should still succeed even if coordinator shutdown fails
        result = await async_unload_entry(hass, mock_config_entry)

        # Check that unload succeeded and cleanup happened
        assert result is True
        # The entry should be removed from the domain data
        assert mock_config_entry.entry_id not in hass.data.get(DOMAIN, {})
        coordinator.async_shutdown.assert_called_once()


@pytest.mark.asyncio
async def test_async_setup_entry_default_task_lookahead(
    hass: HomeAssistant,
    mock_firefly_api: AsyncMock,
) -> None:
    """Test setup uses default task lookahead when not specified."""
    from custom_components.firefly_cloud.const import DEFAULT_TASK_LOOKAHEAD_DAYS

    # Create config entry without task_lookahead_days
    config_entry = Mock()
    config_entry.entry_id = "test-entry-id"
    config_entry.data = {
        "host": "https://testschool.fireflycloud.net",
        "device_id": "test-device-123",
        "secret": "test-secret-456",
        "user_guid": "test-user-789",
    }
    # Mock options properly
    config_entry.options = MagicMock()
    config_entry.options.get = Mock(return_value=None)

    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator") as mock_coordinator_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
        patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True),
    ):
        mock_api_class.return_value = mock_firefly_api
        mock_coordinator = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        result = await async_setup_entry(hass, config_entry)

        assert result is True

        # Verify coordinator was created with default task lookahead
        mock_coordinator_class.assert_called_once()
        call_kwargs = mock_coordinator_class.call_args[1]
        assert call_kwargs["task_lookahead_days"] == DEFAULT_TASK_LOOKAHEAD_DAYS


@pytest.mark.asyncio
async def test_async_setup_entry_credentials_verification_false(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test setup when credential verification returns False."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
    ):
        mock_api = AsyncMock()
        mock_api.verify_credentials.return_value = False  # This will cause the failure before get_api_version
        mock_api_class.return_value = mock_api

        with pytest.raises(ConfigEntryAuthFailed, match="Invalid credentials"):
            await async_setup_entry(hass, mock_config_entry)

        # Verify verify_credentials was called, but get_api_version should not be called
        mock_api.verify_credentials.assert_called_once()
        mock_api.get_api_version.assert_not_called()


@pytest.mark.asyncio
async def test_async_reload_entry_unload_failure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test reload when unload fails."""
    with (
        patch("custom_components.firefly_cloud.async_unload_entry") as mock_unload,
        patch("custom_components.firefly_cloud.async_setup_entry") as mock_setup,
    ):
        mock_unload.return_value = False  # Unload fails
        mock_setup.return_value = True

        await async_reload_entry(hass, mock_config_entry)

        mock_unload.assert_called_once_with(hass, mock_config_entry)
        # Setup should still be called even if unload fails
        mock_setup.assert_called_once_with(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_reload_entry_setup_failure(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
) -> None:
    """Test reload when setup fails."""
    with (
        patch("custom_components.firefly_cloud.async_unload_entry") as mock_unload,
        patch("custom_components.firefly_cloud.async_setup_entry") as mock_setup,
    ):
        mock_unload.return_value = True
        mock_setup.side_effect = ConfigEntryNotReady("Setup failed")

        with pytest.raises(ConfigEntryNotReady):
            await async_reload_entry(hass, mock_config_entry)

        mock_unload.assert_called_once_with(hass, mock_config_entry)
        mock_setup.assert_called_once_with(hass, mock_config_entry)


@pytest.mark.asyncio
async def test_async_setup_entry_creates_api_client_correctly(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_firefly_api: AsyncMock,
) -> None:
    """Test that API client is created with correct parameters."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator") as mock_coordinator_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession") as mock_session_getter,
        patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True),
    ):
        mock_session = Mock()
        mock_session_getter.return_value = mock_session
        mock_api_class.return_value = mock_firefly_api
        mock_coordinator = AsyncMock()
        mock_coordinator_class.return_value = mock_coordinator

        result = await async_setup_entry(hass, mock_config_entry)

        assert result is True

        # Verify API client was created with correct parameters
        mock_api_class.assert_called_once_with(
            session=mock_session,
            host=mock_config_entry.data["host"],
            device_id=mock_config_entry.data["device_id"],
            secret=mock_config_entry.data["secret"],
            user_guid=mock_config_entry.data["user_guid"],
        )

        # Verify session was obtained
        mock_session_getter.assert_called_once_with(hass)


@pytest.mark.asyncio
async def test_async_migrate_entry_version_1(hass: HomeAssistant):
    """Test migration of config entry at version 1 (no-op)."""
    from custom_components.firefly_cloud import async_migrate_entry
    from homeassistant.helpers import entity_registry as er
    from pytest_homeassistant_custom_component.common import MockConfigEntry

    # Create a config entry at version 1
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["child1"],
        },
        version=1,
    )
    config_entry.add_to_hass(hass)

    # Run migration
    result = await async_migrate_entry(hass, config_entry)

    # Should return True (success)
    assert result is True
    # Version should still be 1
    assert config_entry.version == 1
