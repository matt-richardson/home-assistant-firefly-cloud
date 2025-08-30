"""Test the Firefly Cloud init module."""
from unittest.mock import AsyncMock, Mock, patch
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
from custom_components.firefly_cloud.const import DOMAIN
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
    
    with patch.object(
        hass.config_entries, "async_unload_platforms"
    ) as mock_unload_platforms:
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
    
    with patch.object(
        hass.config_entries, "async_unload_platforms"
    ) as mock_unload_platforms:
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