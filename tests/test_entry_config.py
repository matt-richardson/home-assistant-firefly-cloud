"""Tests for reading a config entry's children and settings."""

from types import SimpleNamespace

from custom_components.firefly_cloud.const import CONF_CHILDREN_GUIDS, CONF_SHOW_CLASS_TIMES, CONF_USER_GUID
from custom_components.firefly_cloud.entry_config import child_guids, entry_option


def _entry(data=None, options=None):
    return SimpleNamespace(data=data or {}, options=options or {})


def test_child_guids_are_the_accounts_children():
    """A parent account shows each of its children."""
    entry = _entry({CONF_USER_GUID: "parent", CONF_CHILDREN_GUIDS: ["child-1", "child-2"]})
    assert child_guids(entry) == ["child-1", "child-2"]


def test_child_guids_fall_back_to_the_account_itself():
    """A student account (no children, or the key missing) shows itself."""
    assert child_guids(_entry({CONF_USER_GUID: "student", CONF_CHILDREN_GUIDS: []})) == ["student"]
    assert child_guids(_entry({CONF_USER_GUID: "student"})) == ["student"]


def test_entry_option_prefers_options_then_data_then_default():
    """Options override the setup data, which overrides the default."""
    assert (
        entry_option(_entry({CONF_SHOW_CLASS_TIMES: True}, {CONF_SHOW_CLASS_TIMES: False}), CONF_SHOW_CLASS_TIMES, None)
        is False
    )
    assert entry_option(_entry({CONF_SHOW_CLASS_TIMES: True}), CONF_SHOW_CLASS_TIMES, False) is True
    assert entry_option(_entry(), CONF_SHOW_CLASS_TIMES, "default") == "default"
