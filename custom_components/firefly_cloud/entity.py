"""Base entity class for Firefly Cloud integration."""

from collections.abc import Callable

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SCHOOL_NAME, DOMAIN
from .coordinator import FireflyUpdateCoordinator


class FireflyBaseEntity(CoordinatorEntity[FireflyUpdateCoordinator]):
    """Base entity for Firefly Cloud integration."""

    def __init__(
        self,
        coordinator: FireflyUpdateCoordinator,
        config_entry: ConfigEntry,
        child_guid: str,
        base_name: str,
    ) -> None:
        """Initialize the base entity."""
        super().__init__(coordinator)
        self._child_guid = child_guid
        self._base_name = base_name
        self._attr_name = None
        self._unsub_coordinator: Callable[[], None] | None = None

        school_name = config_entry.data.get(CONF_SCHOOL_NAME, "Firefly Cloud")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"Firefly Cloud - {school_name}",
            manufacturer="Firefly Learning",
            model="Firefly Cloud Integration",
            sw_version="1.0.0",
            configuration_url=config_entry.data.get("host"),
        )

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Subscribe to coordinator updates if not already done by CoordinatorEntity
        if not self._unsub_coordinator:
            self._unsub_coordinator = self.coordinator.async_add_listener(
                self._handle_coordinator_update  # type: ignore[arg-type]
            )

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        if self._unsub_coordinator:
            self._unsub_coordinator()
        await super().async_will_remove_from_hass()

    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        self.async_write_ha_state()

    @property
    def name(self) -> str:
        """Return the display name of the entity."""
        if self.coordinator.data and self._child_guid in self.coordinator.data.get("children_data", {}):
            child_data = self.coordinator.data["children_data"][self._child_guid]
            child_name = child_data.get("name")
            if child_name:
                return f"{self._base_name} ({child_name})"
        return self._attr_name or f"{self._base_name} ({self._child_guid[:8]})"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.coordinator.data is not None
            and self._child_guid in self.coordinator.data.get("children_data", {})
        )

    def _get_child_data(self) -> dict | None:
        """Get data for this child from coordinator.

        Returns None if coordinator data is not available or child doesn't exist.
        This is a helper method to reduce code duplication across entity types.
        """
        if not self.coordinator.data:
            return None

        children_data = self.coordinator.data.get("children_data", {})
        if self._child_guid not in children_data:
            return None

        return children_data[self._child_guid]
