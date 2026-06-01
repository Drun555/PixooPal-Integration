"""Data coordinator for PixooPal."""

from __future__ import annotations

import asyncio
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
    control: dict[str, Any]


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
            status, clockfaces, control = await asyncio.gather(
                self.client.status(),
                self.client.clockfaces(),
                self.client.control(),
            )
        except PixooPalError as err:
            raise UpdateFailed(str(err)) from err

        return PixooPalData(status=status, clockfaces=clockfaces, control=control)

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

    @property
    def pixoo_pal_paused(self) -> bool | None:
        """Return whether PixooPal is paused."""

        if not self.data:
            return None
        value = self.data.control.get("pixooPalOff")
        return bool(value) if isinstance(value, bool) else None

    def async_update_settings(self, changes: dict[str, Any]) -> None:
        """Optimistically update cached Pixoo settings after a successful command."""

        if not self.data:
            return

        status = dict(self.data.status)
        settings = dict(self.settings)
        settings.update(changes)
        status["settings"] = settings
        self.async_set_updated_data(
            PixooPalData(
                status=status,
                clockfaces=self.data.clockfaces,
                control=self.data.control,
            )
        )

    def async_update_control(self, changes: dict[str, Any]) -> None:
        """Optimistically update cached PixooPal control state after a successful command."""

        if not self.data:
            return

        control = dict(self.data.control)
        control.update(changes)
        self.async_set_updated_data(
            PixooPalData(
                status=self.data.status,
                clockfaces=self.data.clockfaces,
                control=control,
            )
        )
