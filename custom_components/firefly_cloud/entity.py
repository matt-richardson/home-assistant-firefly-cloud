"""Base entity class for Firefly Cloud integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_SCHOOL_NAME, DOMAIN
from .coordinator import FireflyUpdateCoordinator
from .models import ChildData


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

        school_name = config_entry.data.get(CONF_SCHOOL_NAME, "Firefly Cloud")
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, config_entry.entry_id)},
            name=f"Firefly Cloud - {school_name}",
            manufacturer="Firefly Learning",
            model="Firefly Cloud Integration",
            configuration_url=config_entry.data.get("host"),
        )

    @property
    def _child(self) -> ChildData | None:
        """Return this child's data, or None if the coordinator has no data for it."""
        if self.coordinator.data is None:
            return None
        return self.coordinator.data.child(self._child_guid)

    @property
    def name(self) -> str:
        """Return the display name of the entity."""
        child = self._child
        if child is not None and child.name:
            return f"{self._base_name} ({child.name})"
        return self._attr_name or f"{self._base_name} ({self._child_guid[:8]})"

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success and self._child is not None
