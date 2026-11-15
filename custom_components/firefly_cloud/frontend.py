"""Serve the dashboard cards from the integration and register them with the frontend."""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.core import HomeAssistant

try:
    from homeassistant.components.http import StaticPathConfig
except ImportError:  # pragma: no cover - Home Assistant before 2024.7
    StaticPathConfig = None  # type: ignore[assignment,misc]

from .const import CARD_FILENAME, DOMAIN, FRONTEND_URL_BASE

_LOGGER = logging.getLogger(__name__)

DATA_FRONTEND_REGISTERED = f"{DOMAIN}_frontend_registered"
WWW_DIR = Path(__file__).parent / "www"


def card_version(directory: Path = WWW_DIR) -> str:
    """Return a short fingerprint of the card files, used as the cards' ?v= tag.

    Any change to the files gives the cards a new URL, so browsers (and HA's frontend
    cache) load the new cards instead of cached older ones.
    """
    digest = hashlib.sha256()
    for path in sorted(directory.glob("*.js")):
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()[:12]


async def async_register_frontend(hass: HomeAssistant) -> None:
    """Serve the cards' files and register them as a frontend module, once per instance.

    Skips the module registration (with a debug log) when the frontend component
    isn't loaded, e.g. on a headless install, so integration setup still succeeds.
    """
    if hass.data.get(DATA_FRONTEND_REGISTERED):
        return
    hass.data[DATA_FRONTEND_REGISTERED] = True

    if StaticPathConfig is not None:
        await hass.http.async_register_static_paths([StaticPathConfig(FRONTEND_URL_BASE, str(WWW_DIR), False)])
    else:
        hass.http.register_static_path(FRONTEND_URL_BASE, str(WWW_DIR), False)  # type: ignore[attr-defined]
    if "frontend" not in hass.config.components:
        _LOGGER.debug("Frontend not loaded; not registering the Firefly cards")
        return
    version = await hass.async_add_executor_job(card_version)
    add_extra_js_url(hass, f"{FRONTEND_URL_BASE}/{CARD_FILENAME}?v={version}")
