"""PixooPal light platform."""

from __future__ import annotations

import asyncio
from math import ceil
from typing import Any

from homeassistant.components.light import ATTR_BRIGHTNESS, ColorMode, LightEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util.color import brightness_to_value, value_to_brightness

from .coordinator import PixooPalCoordinator
from .entity import PixooPalEntity

PIXOO_BRIGHTNESS_SCALE = (0, 100)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up PixooPal light."""

    async_add_entities([PixooPalBrightnessLight(entry.runtime_data, entry.entry_id)])


class PixooPalBrightnessLight(PixooPalEntity, LightEntity):
    """Light entity controlling Pixoo brightness and screen power."""

    _attr_name = "Display"
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}

    def __init__(self, coordinator: PixooPalCoordinator, entry_id: str) -> None:
        """Initialize the light."""

        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_display"

    @property
    def is_on(self) -> bool | None:
        """Return whether the Pixoo screen is on."""

        light_switch = self.coordinator.settings.get("LightSwitch")
        if isinstance(light_switch, int | float):
            return int(light_switch) == 1
        return self.coordinator.reachable

    @property
    def brightness(self) -> int | None:
        """Return current brightness in Home Assistant's 1..255 range."""

        value = self.coordinator.settings.get("Brightness")
        if not isinstance(value, int | float):
            return None
        return value_to_brightness(PIXOO_BRIGHTNESS_SCALE, int(value))

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Turn the Pixoo screen on and optionally set brightness."""

        settings: dict[str, Any] = {"LightSwitch": 1}
        commands = []
        if ATTR_BRIGHTNESS in kwargs:
            brightness = ceil(brightness_to_value(PIXOO_BRIGHTNESS_SCALE, kwargs[ATTR_BRIGHTNESS]))
            commands.append(self.coordinator.client.set_brightness(brightness))
            settings["Brightness"] = brightness

        if self.is_on is not True:
            commands.append(self.coordinator.client.set_screen(True))

        if commands:
            await self.async_call_client(asyncio.gather(*commands))

        self.coordinator.async_update_settings(settings)
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Turn the Pixoo screen off."""

        await self.async_call_client(self.coordinator.client.set_screen(False))
        self.coordinator.async_update_settings({"LightSwitch": 0})
        self.async_write_ha_state()
