"""The Firefly Cloud integration."""
import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, ConfigEntryNotReady
from homeassistant.helpers import aiohttp_client

from .api import FireflyAPIClient
from .const import (
    CONF_CHILDREN_GUIDS,
    CONF_DEVICE_ID,
    CONF_HOST,
    CONF_SECRET,
    CONF_TASK_LOOKAHEAD_DAYS,
    CONF_USER_GUID,
    DEFAULT_TASK_LOOKAHEAD_DAYS,
    DOMAIN,
    PARALLEL_UPDATES,
)
from .coordinator import FireflyUpdateCoordinator
from .exceptions import (
    FireflyAuthenticationError,
    FireflyConnectionError,
    FireflyTokenExpiredError,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Firefly Cloud from a config entry."""
    _LOGGER.debug("Setting up Firefly Cloud integration for %s", entry.title)

    # Get configuration data
    host = entry.data[CONF_HOST]
    device_id = entry.data[CONF_DEVICE_ID]
    secret = entry.data[CONF_SECRET]
    user_guid = entry.data[CONF_USER_GUID]
    children_guids = entry.data.get(CONF_CHILDREN_GUIDS, [])

    # Get task lookahead days from options or data
    task_lookahead_days = (
        entry.options.get(CONF_TASK_LOOKAHEAD_DAYS) or
        entry.data.get(CONF_TASK_LOOKAHEAD_DAYS, DEFAULT_TASK_LOOKAHEAD_DAYS)
    )

    # Create HTTP session
    session = aiohttp_client.async_get_clientsession(hass)

    # Create API client
    api = FireflyAPIClient(
        session=session,
        host=host,
        device_id=device_id,
        secret=secret,
        user_guid=user_guid,
    )

    try:
        # Verify credentials are still valid
        if not await api.verify_credentials():
            _LOGGER.warning(
                "Firefly credentials are invalid, reauthentication required")
            raise ConfigEntryAuthFailed("Invalid credentials")

        # Test API connectivity
        await api.get_api_version()

        _LOGGER.info("Successfully connected to Firefly at %s", host)

    except ConfigEntryAuthFailed:
        # Re-raise ConfigEntryAuthFailed as-is
        raise
    except FireflyTokenExpiredError as err:
        _LOGGER.warning("Firefly authentication token expired")
        raise ConfigEntryAuthFailed("Authentication token expired") from err
    except FireflyAuthenticationError as err:
        _LOGGER.error("Firefly authentication failed: %s", err)
        raise ConfigEntryAuthFailed(f"Authentication failed: {err}") from err
    except FireflyConnectionError as err:
        _LOGGER.error("Failed to connect to Firefly: %s", err)
        raise ConfigEntryNotReady(f"Failed to connect: {err}") from err
    except Exception as err:
        _LOGGER.exception("Unexpected error setting up Firefly Cloud")
        raise ConfigEntryNotReady(f"Unexpected error: {err}") from err

    # Create update coordinator
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=api,
        task_lookahead_days=task_lookahead_days,
        children_guids=children_guids,
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception as err:
        _LOGGER.error("Failed to fetch initial data from Firefly: %s", err)
        raise ConfigEntryNotReady(
            f"Failed to fetch initial data: {err}") from err

    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info(
        "Firefly Cloud integration setup completed for %s", entry.title)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.debug("Unloading Firefly Cloud integration for %s", entry.title)

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        # Remove coordinator from hass.data
        coordinator = hass.data[DOMAIN].pop(entry.entry_id)

        # Stop the coordinator's update loop
        if coordinator:
            try:
                await coordinator.async_shutdown()
            except Exception as err:
                _LOGGER.warning("Error shutting down coordinator: %s", err)

        # Clean up hass.data if this was the last entry
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)

    _LOGGER.info("Firefly Cloud integration unloaded for %s", entry.title)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.debug("Reloading Firefly Cloud integration for %s", entry.title)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.debug(
        "Updating options for Firefly Cloud integration %s", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating Firefly Cloud entry from version %s",
                  config_entry.version)

    if config_entry.version == 1:
        # No migration needed yet, we're at version 1
        pass

    # Always update version to current
    hass.config_entries.async_update_entry(config_entry, version=1)
    _LOGGER.info("Migration of Firefly Cloud entry completed")
    return True
