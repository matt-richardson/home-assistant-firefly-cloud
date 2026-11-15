"""The Firefly Cloud integration."""

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
)
from .coordinator import FireflyUpdateCoordinator
from .exceptions import FireflyAuthenticationError, FireflyConnectionError, FireflyTokenExpiredError
from .frontend import async_register_frontend
from .services import async_setup_services, async_unload_services
from .task_changes import TaskChangeStore
from .websocket_api import async_register_websocket_api

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.CALENDAR, Platform.SENSOR, Platform.TODO]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:  # pylint: disable=too-many-statements
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
        entry.options.get(CONF_TASK_LOOKAHEAD_DAYS)
        or entry.data.get(CONF_TASK_LOOKAHEAD_DAYS)
        or DEFAULT_TASK_LOOKAHEAD_DAYS
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
            _LOGGER.warning("Firefly credentials are invalid, reauthentication required")
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

    # Due date changes made on the dashboard (kept in Home Assistant, not Firefly)
    change_store = TaskChangeStore(hass, entry.entry_id)
    await change_store.async_load()

    # Create update coordinator
    coordinator = FireflyUpdateCoordinator(
        hass=hass,
        api=api,
        task_lookahead_days=task_lookahead_days,
        children_guids=children_guids,
        change_store=change_store,
    )

    # Fetch initial data
    try:
        await coordinator.async_config_entry_first_refresh()
    except (ConfigEntryAuthFailed, ConfigEntryNotReady):
        # Let Home Assistant start reauthentication or retry setup as these ask
        raise
    except Exception as err:
        _LOGGER.error("Failed to fetch initial data from Firefly: %s", err)
        raise ConfigEntryNotReady(f"Failed to fetch initial data: {err}") from err

    # Store coordinator in hass.data
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    async_setup_services(hass)
    async_register_websocket_api(hass)
    await async_register_frontend(hass)

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Set up options update listener
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    _LOGGER.info("Firefly Cloud integration setup completed for %s", entry.title)
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
            except Exception as err:  # pylint: disable=broad-except
                _LOGGER.warning("Error shutting down coordinator: %s", err)

        # Then write any pending task change save (and stop saving) before a reload or removal
        if coordinator and getattr(coordinator, "change_store", None) is not None:
            await coordinator.change_store.async_flush()

        # Clean up hass.data if this was the last entry
        if not hass.data[DOMAIN]:
            hass.data.pop(DOMAIN)
            async_unload_services(hass)

    _LOGGER.info("Firefly Cloud integration unloaded for %s", entry.title)
    return unload_ok


async def async_remove_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Delete the entry's saved task changes when it's removed."""
    await TaskChangeStore(hass, entry.entry_id).async_remove()


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    _LOGGER.debug("Reloading Firefly Cloud integration for %s", entry.title)
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)


async def async_update_options(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Update options."""
    _LOGGER.debug("Updating options for Firefly Cloud integration %s", entry.title)
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug("Migrating Firefly Cloud entry from version %s", config_entry.version)

    if config_entry.version == 1:
        # No migration needed yet, we're at version 1
        pass

    # Always update version to current
    hass.config_entries.async_update_entry(config_entry, version=1)
    _LOGGER.info("Migration of Firefly Cloud entry completed")
    return True
