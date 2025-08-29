"""Config flow for Firefly Cloud integration."""
import logging
from typing import Any, Dict, Optional

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import aiohttp_client

from .api import FireflyAPIClient
from .const import (
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
from .exceptions import (
    FireflyAuthenticationError,
    FireflyConnectionError,
    FireflySchoolNotFoundError,
)

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema({
    vol.Required(CONF_SCHOOL_CODE): str,
})

STEP_AUTH_DATA_SCHEMA = vol.Schema({
    vol.Required("auth_response"): str,
})


class FireflyCloudConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Firefly Cloud."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._school_info: Optional[Dict[str, Any]] = None
        self._api_client: Optional[FireflyAPIClient] = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Get school information
                session = aiohttp_client.async_get_clientsession(self.hass)
                self._school_info = await FireflyAPIClient.get_school_info(
                    session, user_input[CONF_SCHOOL_CODE]
                )

                if not self._school_info["enabled"]:
                    errors["base"] = "school_disabled"
                else:
                    # Check for existing entries with the same school
                    await self.async_set_unique_id(user_input[CONF_SCHOOL_CODE])
                    self._abort_if_unique_id_configured()

                    # Create API client for authentication
                    self._api_client = FireflyAPIClient(
                        session=session,
                        host=self._school_info["url"],
                        device_id=self._school_info["device_id"],
                        secret="",  # Will be set after authentication
                    )

                    return await self.async_step_auth()

            except FireflySchoolNotFoundError:
                errors["base"] = "school_not_found"
            except FireflyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during school lookup")
                errors["base"] = "unknown"

        return self.async_show_form(
            step_id="user",
            data_schema=STEP_USER_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "school_code_help": "Enter your school's Firefly code (usually found in your school's Firefly URL)"
            },
        )

    async def async_step_auth(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle the authentication step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Parse authentication response
                auth_data = await self._api_client.parse_authentication_response(
                    user_input["auth_response"]
                )

                # Update API client with secret
                self._api_client._secret = auth_data["secret"]

                # Verify credentials work
                if not await self._api_client.verify_credentials():
                    errors["base"] = "invalid_auth"
                else:
                    # Get user info to validate
                    user_info = await self._api_client.get_user_info()
                    
                    # Create the config entry
                    return self.async_create_entry(
                        title=f"{self._school_info['name']} - {user_info['fullname']}",
                        data={
                            CONF_SCHOOL_CODE: self.unique_id,
                            CONF_SCHOOL_NAME: self._school_info["name"],
                            CONF_HOST: self._school_info["url"],
                            CONF_DEVICE_ID: self._school_info["device_id"],
                            CONF_SECRET: auth_data["secret"],
                            CONF_USER_GUID: user_info["guid"],
                            CONF_TASK_LOOKAHEAD_DAYS: DEFAULT_TASK_LOOKAHEAD_DAYS,
                        },
                    )

            except FireflyAuthenticationError:
                errors["base"] = "invalid_auth"
            except FireflyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during authentication")
                errors["base"] = "unknown"

        # Show authentication form with browser redirect URL
        auth_url = self._api_client.get_auth_url()
        
        return self.async_show_form(
            step_id="auth",
            data_schema=STEP_AUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "auth_url": auth_url,
                "device_id": self._school_info["device_id"],
                "instructions": (
                    "1. Click the link above to open Firefly in your browser\n"
                    "2. Log in with your Firefly credentials\n"
                    "3. After successful login, open browser developer tools (F12)\n"
                    "4. Go to Console tab and type: document.documentElement.outerHTML\n"
                    "5. Copy the entire response (it should contain <token>...</token>)\n"
                    "6. Paste it in the field below"
                ),
            },
        )

    async def async_step_reauth(
        self, entry_data: Dict[str, Any]
    ) -> FlowResult:
        """Handle reauthentication."""
        # Store the entry for later use
        self.context["entry_id"] = entry_data.get("entry_id")
        
        # Recreate school info from stored data
        self._school_info = {
            "name": entry_data.get(CONF_SCHOOL_NAME),
            "url": entry_data.get(CONF_HOST),
            "device_id": entry_data.get(CONF_DEVICE_ID),
        }

        # Create API client for reauthentication
        session = aiohttp_client.async_get_clientsession(self.hass)
        self._api_client = FireflyAPIClient(
            session=session,
            host=self._school_info["url"],
            device_id=self._school_info["device_id"],
            secret="",  # Will be set after authentication
        )

        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Handle reauthentication confirmation."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            try:
                # Parse authentication response
                auth_data = await self._api_client.parse_authentication_response(
                    user_input["auth_response"]
                )

                # Update API client with secret
                self._api_client._secret = auth_data["secret"]

                # Verify credentials work
                if not await self._api_client.verify_credentials():
                    errors["base"] = "invalid_auth"
                else:
                    # Update the existing config entry
                    entry_id = self.context["entry_id"]
                    entry = self.hass.config_entries.async_get_entry(entry_id)
                    
                    if entry:
                        new_data = entry.data.copy()
                        new_data[CONF_SECRET] = auth_data["secret"]
                        
                        self.hass.config_entries.async_update_entry(
                            entry, data=new_data
                        )
                        
                        # Reload the integration
                        await self.hass.config_entries.async_reload(entry_id)
                        
                        return self.async_abort(reason="reauth_successful")

            except FireflyAuthenticationError:
                errors["base"] = "invalid_auth"
            except FireflyConnectionError:
                errors["base"] = "cannot_connect"
            except Exception:  # pylint: disable=broad-except
                _LOGGER.exception("Unexpected error during reauthentication")
                errors["base"] = "unknown"

        # Show reauthentication form
        auth_url = self._api_client.get_auth_url()
        
        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=STEP_AUTH_DATA_SCHEMA,
            errors=errors,
            description_placeholders={
                "auth_url": auth_url,
                "device_id": self._school_info["device_id"],
                "instructions": (
                    "Your Firefly authentication has expired. Please log in again:\n\n"
                    "1. Click the link above to open Firefly in your browser\n"
                    "2. Log in with your Firefly credentials\n"
                    "3. After successful login, open browser developer tools (F12)\n"
                    "4. Go to Console tab and type: document.documentElement.outerHTML\n"
                    "5. Copy the entire response (it should contain <token>...</token>)\n"
                    "6. Paste it in the field below"
                ),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "FireflyCloudOptionsFlowHandler":
        """Get the options flow for this handler."""
        return FireflyCloudOptionsFlowHandler(config_entry)


class FireflyCloudOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle Firefly Cloud options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: Optional[Dict[str, Any]] = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        options_schema = vol.Schema({
            vol.Optional(
                CONF_TASK_LOOKAHEAD_DAYS,
                default=self.config_entry.options.get(
                    CONF_TASK_LOOKAHEAD_DAYS,
                    self.config_entry.data.get(CONF_TASK_LOOKAHEAD_DAYS, DEFAULT_TASK_LOOKAHEAD_DAYS)
                ),
            ): vol.All(int, vol.Range(min=1, max=30)),
        })

        return self.async_show_form(
            step_id="init",
            data_schema=options_schema,
            description_placeholders={
                "task_lookahead_help": "Number of days ahead to look for upcoming tasks (1-30 days)"
            },
        )