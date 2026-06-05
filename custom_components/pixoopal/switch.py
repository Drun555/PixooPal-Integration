"""PixooPal switch platform."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PixooPalCoordinator
from .entity import PixooPalEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up PixooPal switches."""

    async_add_entities([PixooPalPauseSwitch(entry.runtime_data, entry.entry_id)])


class PixooPalPauseSwitch(PixooPalEntity, SwitchEntity):
    """Switch entity controlling PixooPal pause state."""

    _attr_name = "Pause PixooPal"
    _attr_icon = "mdi:pause-circle"

    def __init__(self, coordinator: PixooPalCoordinator, entry_id: str) -> None:
        """Initialize the switch."""

        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_pause_pixoopal"

    @property
    def is_on(self) -> bool | None:
        """Return whether PixooPal is paused."""

        return self.coordinator.pixoo_pal_paused

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Pause PixooPal."""

        await self.async_call_client(self.coordinator.client.set_pixoo_pal_paused(True))
        self.coordinator.async_update_control({"pixooPalOff": True})
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Resume PixooPal."""

        await self.async_call_client(self.coordinator.client.set_pixoo_pal_paused(False))
        self.coordinator.async_update_control({"pixooPalOff": False})
        self.async_write_ha_state()
