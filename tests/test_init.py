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


@pytest.fixture(autouse=True)
def mock_register_frontend():
    """Setup tests run without an HTTP server; card serving is covered in test_frontend.py."""
    with patch("custom_components.firefly_cloud.async_register_frontend", new=AsyncMock()) as register:
        yield register


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
async def test_async_setup_entry_first_refresh_auth_failure_starts_reauth(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_firefly_api: AsyncMock,
) -> None:
    """An auth failure on the first fetch stays an auth failure, so Home Assistant asks to log in again."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient") as mock_api_class,
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator") as mock_coordinator_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
    ):
        mock_api_class.return_value = mock_firefly_api
        mock_coordinator = AsyncMock()
        mock_coordinator.async_config_entry_first_refresh.side_effect = ConfigEntryAuthFailed("Token expired")
        mock_coordinator_class.return_value = mock_coordinator

        with pytest.raises(ConfigEntryAuthFailed, match="Token expired"):
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
    from types import MappingProxyType

    from conftest import create_config_entry_with_version_compat

    from custom_components.firefly_cloud import async_migrate_entry

    # Create a config entry at version 1
    config_entry = create_config_entry_with_version_compat(
        domain=DOMAIN,
        title="Test School - User",
        data={
            CONF_SCHOOL_CODE: "testschool",
            CONF_SCHOOL_NAME: "Test School",
            CONF_HOST: "https://testschool.fireflycloud.net",
            CONF_DEVICE_ID: "test-device-123",
            CONF_SECRET: "test-secret-456",
            CONF_USER_GUID: "test-user-789",
            CONF_CHILDREN_GUIDS: ["child1"],
        },
        options={},
        version=1,
        minor_version=1,
        source="user",
        unique_id="testschool",
        entry_id="test-entry-migration",
        discovery_keys=MappingProxyType({}),
    )
    hass.config_entries._entries[config_entry.entry_id] = config_entry

    # Run migration
    result = await async_migrate_entry(hass, config_entry)

    # Should return True (success)
    assert result is True
    # Version should still be 1
    assert config_entry.version == 1


@pytest.mark.asyncio
async def test_setup_loads_change_store_and_passes_it(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_firefly_api: AsyncMock,
) -> None:
    """Setup loads the entry's task change store and gives it to the coordinator."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient", return_value=mock_firefly_api),
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator") as mock_coordinator_class,
        patch("custom_components.firefly_cloud.TaskChangeStore") as mock_store_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
        patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True),
    ):
        mock_coordinator_class.return_value = AsyncMock()
        mock_store_class.return_value.async_load = AsyncMock()

        assert await async_setup_entry(hass, mock_config_entry) is True

    mock_store_class.assert_called_once_with(hass, mock_config_entry.entry_id)
    mock_store_class.return_value.async_load.assert_awaited_once()
    assert mock_coordinator_class.call_args.kwargs["change_store"] is mock_store_class.return_value


@pytest.mark.asyncio
async def test_remove_entry_removes_store(hass: HomeAssistant, mock_config_entry: ConfigEntry) -> None:
    """Removing the config entry deletes its saved task changes."""
    from custom_components.firefly_cloud import async_remove_entry

    with patch("custom_components.firefly_cloud.TaskChangeStore") as mock_store_class:
        mock_store_class.return_value.async_remove = AsyncMock()
        await async_remove_entry(hass, mock_config_entry)

    mock_store_class.assert_called_once_with(hass, mock_config_entry.entry_id)
    mock_store_class.return_value.async_remove.assert_awaited_once()


@pytest.mark.asyncio
async def test_setup_registers_services_and_last_unload_removes_them(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_firefly_api: AsyncMock,
) -> None:
    """The due date services exist while an entry is loaded and go when the last one unloads."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient", return_value=mock_firefly_api),
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator", return_value=AsyncMock()),
        patch("custom_components.firefly_cloud.TaskChangeStore") as mock_store_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
        patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True),
    ):
        mock_store_class.return_value.async_load = AsyncMock()
        await async_setup_entry(hass, mock_config_entry)

    assert hass.services.has_service(DOMAIN, "set_task_due_date")
    assert hass.services.has_service(DOMAIN, "clear_task_due_date")

    with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
        await async_unload_entry(hass, mock_config_entry)

    assert not hass.services.has_service(DOMAIN, "set_task_due_date")


@pytest.mark.asyncio
async def test_setup_registers_frontend(
    hass: HomeAssistant,
    mock_config_entry: ConfigEntry,
    mock_firefly_api: AsyncMock,
    mock_register_frontend: AsyncMock,
) -> None:
    """Setup serves and registers the dashboard cards."""
    with (
        patch("custom_components.firefly_cloud.FireflyAPIClient", return_value=mock_firefly_api),
        patch("custom_components.firefly_cloud.FireflyUpdateCoordinator", return_value=AsyncMock()),
        patch("custom_components.firefly_cloud.TaskChangeStore") as mock_store_class,
        patch("homeassistant.helpers.aiohttp_client.async_get_clientsession"),
        patch.object(hass.config_entries, "async_forward_entry_setups", return_value=True),
    ):
        mock_store_class.return_value.async_load = AsyncMock()
        await async_setup_entry(hass, mock_config_entry)

    mock_register_frontend.assert_awaited_once_with(hass)


@pytest.mark.asyncio
async def test_unload_flushes_pending_changes(hass: HomeAssistant, mock_config_entry: ConfigEntry) -> None:
    """Unloading writes any pending task change save before the entry goes away."""
    coordinator = AsyncMock()
    coordinator.change_store.async_flush = AsyncMock()
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coordinator

    with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
        assert await async_unload_entry(hass, mock_config_entry) is True

    coordinator.change_store.async_flush.assert_awaited_once()


@pytest.mark.asyncio
async def test_unload_stops_coordinator_before_flushing(hass: HomeAssistant, mock_config_entry: ConfigEntry) -> None:
    """The coordinator is shut down before the final save, so no poll can save after it."""
    calls = []
    coordinator = AsyncMock()
    coordinator.async_shutdown = AsyncMock(side_effect=lambda: calls.append("shutdown"))
    coordinator.change_store.async_flush = AsyncMock(side_effect=lambda: calls.append("flush"))
    hass.data.setdefault(DOMAIN, {})[mock_config_entry.entry_id] = coordinator

    with patch.object(hass.config_entries, "async_unload_platforms", return_value=True):
        await async_unload_entry(hass, mock_config_entry)

    assert calls == ["shutdown", "flush"]
