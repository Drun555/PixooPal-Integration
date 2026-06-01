"""PixooPal notify platform."""

from __future__ import annotations

from homeassistant.components.notify import NotifyEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PixooPalCoordinator
from .entity import PixooPalEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up PixooPal notify."""

    async_add_entities([PixooPalNotifyEntity(entry.runtime_data, entry.entry_id)])


class PixooPalNotifyEntity(PixooPalEntity, NotifyEntity):
    """Notify entity that shows messages on Pixoo via PixooPal."""

    _attr_name = "Notify"

    def __init__(self, coordinator: PixooPalCoordinator, entry_id: str) -> None:
        """Initialize the notify entity."""

        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_notify"

    async def async_send_message(self, message: str, title: str | None = None) -> None:
        """Send a notification message to PixooPal."""

        text = f"{title}: {message}" if title else message

        await self.coordinator.client.notify(text)
        await self.coordinator.async_request_refresh()
