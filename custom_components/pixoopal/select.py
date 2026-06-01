"""PixooPal select platform."""

from __future__ import annotations

from typing import Any

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PixooPalCoordinator
from .entity import PixooPalEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up PixooPal select."""

    async_add_entities([PixooPalClockfaceSelect(entry.runtime_data, entry.entry_id)])


class PixooPalClockfaceSelect(PixooPalEntity, SelectEntity):
    """Select entity for the active PixooPal clockface."""

    _attr_name = "Clockface"

    def __init__(self, coordinator: PixooPalCoordinator, entry_id: str) -> None:
        """Initialize the select."""

        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_clockface"

    @property
    def options(self) -> list[str]:
        """Return available clockface labels."""

        return [label for label, _clockface_id in self._label_id_pairs()]

    @property
    def current_option(self) -> str | None:
        """Return the current clockface label."""

        if not self.coordinator.data:
            return None

        active_id = self.coordinator.data.clockfaces.get("activeId")
        for label, clockface_id in self._label_id_pairs():
            if clockface_id == active_id:
                return label
        return None

    async def async_select_option(self, option: str) -> None:
        """Select a clockface by its label."""

        clockface_id = dict(self._label_id_pairs()).get(option)
        if clockface_id is None:
            return

        await self.coordinator.client.set_clockface(clockface_id)
        await self.coordinator.async_request_refresh()

    def _label_id_pairs(self) -> list[tuple[str, str]]:
        clockfaces = []
        if self.coordinator.data:
            value = self.coordinator.data.clockfaces.get("clockfaces")
            if isinstance(value, list):
                clockfaces = [item for item in value if isinstance(item, dict)]

        names = [str(item.get("name") or item.get("id") or "") for item in clockfaces]
        duplicates = {name for name in names if names.count(name) > 1}

        pairs: list[tuple[str, str]] = []
        for item in clockfaces:
            clockface_id = str(item.get("id") or "")
            name = str(item.get("name") or clockface_id)
            if not clockface_id:
                continue
            label = f"{name} ({clockface_id})" if name in duplicates else name
            pairs.append((label, clockface_id))
        return pairs
