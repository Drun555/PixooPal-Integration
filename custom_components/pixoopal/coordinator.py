"""Data coordinator for PixooPal."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
import logging
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .client import PixooPalClient, PixooPalError
from .const import DEFAULT_SCAN_INTERVAL_SECONDS, DOMAIN

_LOGGER = logging.getLogger(__name__)


@dataclass
class PixooPalData:
    """Latest PixooPal data used by entities."""

    status: dict[str, Any]
    clockfaces: dict[str, Any]


class PixooPalCoordinator(DataUpdateCoordinator[PixooPalData]):
    """Coordinate PixooPal polling."""

    def __init__(self, hass: HomeAssistant, client: PixooPalClient) -> None:
        """Initialize the coordinator."""

        super().__init__(
            hass,
            logger=_LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=DEFAULT_SCAN_INTERVAL_SECONDS),
        )
        self.client = client

    async def _async_update_data(self) -> PixooPalData:
        """Fetch current PixooPal state."""

        try:
            status = await self.client.status()
            clockfaces = await self.client.clockfaces()
        except PixooPalError as err:
            raise UpdateFailed(str(err)) from err

        return PixooPalData(status=status, clockfaces=clockfaces)

    @property
    def reachable(self) -> bool:
        """Return whether PixooPal and the Pixoo device are reachable."""

        return bool(self.data and self.data.status.get("reachable", False))

    @property
    def settings(self) -> dict[str, Any]:
        """Return Pixoo settings from the latest status."""

        if not self.data:
            return {}
        settings = self.data.status.get("settings")
        return settings if isinstance(settings, dict) else {}
