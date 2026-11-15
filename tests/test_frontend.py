"""Tests for serving and registering the dashboard cards."""

import re
from collections import namedtuple
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from custom_components.firefly_cloud.const import CARD_FILENAME, FRONTEND_URL_BASE
from custom_components.firefly_cloud.frontend import WWW_DIR, async_register_frontend, card_version

# Stands in for homeassistant.components.http.StaticPathConfig, which older Home Assistant (CI runs 2024.3) lacks
FakeStaticPathConfig = namedtuple("FakeStaticPathConfig", ["url_path", "path", "cache_headers"])


@pytest.fixture
def modern_static_paths():
    """Test the StaticPathConfig code path whatever Home Assistant version is installed."""
    with patch("custom_components.firefly_cloud.frontend.StaticPathConfig", FakeStaticPathConfig):
        yield


@pytest.fixture
def fake_hass():
    """A hass with http, an executor and optionally the frontend loaded."""
    hass = MagicMock()
    hass.data = {}
    hass.http.async_register_static_paths = AsyncMock()
    hass.config.components = {"frontend"}

    async def run(func, *args):
        return func(*args)

    hass.async_add_executor_job = run
    return hass


@pytest.mark.asyncio
async def test_registers_static_path_and_module(fake_hass, modern_static_paths):
    """The www folder is served and the cards module is added to the frontend with a version."""
    with patch("custom_components.firefly_cloud.frontend.add_extra_js_url") as add:
        await async_register_frontend(fake_hass)

    [config] = fake_hass.http.async_register_static_paths.call_args.args[0]
    assert config.url_path == FRONTEND_URL_BASE == "/firefly_cloud_frontend"
    assert config.path == str(WWW_DIR)
    url = add.call_args.args[1]
    assert re.fullmatch(r"/firefly_cloud_frontend/firefly-cards\.js\?v=[0-9a-f]{12}", url)
    assert CARD_FILENAME == "firefly-cards.js"


@pytest.mark.asyncio
async def test_registers_once(fake_hass, modern_static_paths):
    """A second config entry doesn't register the cards again."""
    with patch("custom_components.firefly_cloud.frontend.add_extra_js_url") as add:
        await async_register_frontend(fake_hass)
        await async_register_frontend(fake_hass)
    assert add.call_count == 1
    assert fake_hass.http.async_register_static_paths.await_count == 1


@pytest.mark.asyncio
async def test_skips_module_without_frontend(fake_hass, modern_static_paths):
    """Without the frontend (headless), files are served but no module is added."""
    fake_hass.config.components = set()
    with patch("custom_components.firefly_cloud.frontend.add_extra_js_url") as add:
        await async_register_frontend(fake_hass)
    add.assert_not_called()
    fake_hass.http.async_register_static_paths.assert_awaited_once()


def test_card_version_changes_with_files(tmp_path):
    """Any change to a card file gives a new version."""
    (tmp_path / "a.js").write_text("one")
    first = card_version(tmp_path)
    (tmp_path / "a.js").write_text("two")
    assert card_version(tmp_path) != first
    assert len(first) == 12


def test_entry_module_imports_both_cards():
    """The single registered module loads both cards with its own version."""
    source = (WWW_DIR / CARD_FILENAME).read_text()
    assert "./firefly-tasks-card.js" in source
    assert "./firefly-classes-card.js" in source


@pytest.mark.asyncio
async def test_registers_static_path_on_older_home_assistant(fake_hass):
    """Before StaticPathConfig existed (HA < 2024.7), the older static path API is used."""
    fake_hass.http.register_static_path = MagicMock()
    with (
        patch("custom_components.firefly_cloud.frontend.StaticPathConfig", None),
        patch("custom_components.firefly_cloud.frontend.add_extra_js_url") as add,
    ):
        await async_register_frontend(fake_hass)
    fake_hass.http.register_static_path.assert_called_once_with(FRONTEND_URL_BASE, str(WWW_DIR), False)
    fake_hass.http.async_register_static_paths.assert_not_awaited()
    add.assert_called_once()
