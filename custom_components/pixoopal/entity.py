"""Shared PixooPal entity helpers."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER, MODEL
from .coordinator import PixooPalCoordinator


class PixooPalEntity(CoordinatorEntity[PixooPalCoordinator]):
    """Base class for PixooPal entities."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: PixooPalCoordinator, entry_id: str) -> None:
        """Initialize the entity."""

        super().__init__(coordinator)
        self._entry_id = entry_id
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            manufacturer=MANUFACTURER,
            model=MODEL,
            name="PixooPal",
            configuration_url=coordinator.client.base_url,
        )

    @property
    def available(self) -> bool:
        """Return entity availability."""

        return self.coordinator.last_update_success
