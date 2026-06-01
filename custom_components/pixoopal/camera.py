"""PixooPal camera platform."""

from __future__ import annotations

from homeassistant.components.camera import Camera, CameraEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .coordinator import PixooPalCoordinator
from .entity import PixooPalEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up PixooPal camera."""

    async_add_entities([PixooPalCamera(entry.runtime_data, entry.entry_id)])


class PixooPalCamera(PixooPalEntity, Camera):
    """Camera entity exposing PixooPal MJPEG preview."""

    _attr_name = "Preview"
    _attr_supported_features = CameraEntityFeature.STREAM

    def __init__(self, coordinator: PixooPalCoordinator, entry_id: str) -> None:
        """Initialize the camera."""

        Camera.__init__(self)
        PixooPalEntity.__init__(self, coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_preview"

    async def stream_source(self) -> str | None:
        """Return the MJPEG stream source."""

        return self.coordinator.client.url("/api/v1/preview.mjpeg")

    async def async_camera_image(
        self, width: int | None = None, height: int | None = None
    ) -> bytes | None:
        """Return a still image for the camera entity."""

        return await self.coordinator.client.camera_image()
