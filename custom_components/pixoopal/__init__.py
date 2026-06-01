"""PixooPal Home Assistant integration."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import PixooPalClient
from .const import CONF_BASE_URL, DOMAIN, PLATFORMS
from .coordinator import PixooPalCoordinator
from .http import PixooPalEntriesView, PixooPalProxyView

type PixooPalConfigEntry = ConfigEntry[PixooPalCoordinator]

SERVICE_NOTIFY = "notify"
ATTR_MESSAGE = "message"
ATTR_TITLE = "title"
ATTR_BEEP = "beep"
ATTR_ENTRY_ID = "entry_id"

NOTIFY_SERVICE_SCHEMA = vol.Schema(
    {
        vol.Required(ATTR_MESSAGE): str,
        vol.Optional(ATTR_TITLE): str,
        vol.Optional(ATTR_BEEP, default=False): bool,
        vol.Optional(ATTR_ENTRY_ID): str,
    }
)


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration-level HTTP resources."""

    hass.http.register_view(PixooPalEntriesView)
    hass.http.register_view(PixooPalProxyView)

    async def async_handle_notify(call: ServiceCall) -> None:
        """Handle the PixooPal notify action."""

        entry_id = call.data.get(ATTR_ENTRY_ID)
        entries = [
            entry
            for entry in hass.config_entries.async_entries(DOMAIN)
            if entry_id in (None, entry.entry_id)
        ]

        loaded_entries = [entry for entry in entries if getattr(entry, "runtime_data", None)]

        if not loaded_entries:
            raise HomeAssistantError("No loaded PixooPal config entry found")

        if entry_id is None and len(loaded_entries) > 1:
            raise HomeAssistantError("Multiple PixooPal entries found; provide entry_id")

        entry = loaded_entries[0]
        coordinator = entry.runtime_data
        title = call.data.get(ATTR_TITLE)
        message = call.data[ATTR_MESSAGE]
        text = f"{title}: {message}" if title else message

        await coordinator.client.notify(text, call.data[ATTR_BEEP])
        await coordinator.async_request_refresh()

    hass.services.async_register(
        DOMAIN,
        SERVICE_NOTIFY,
        async_handle_notify,
        schema=NOTIFY_SERVICE_SCHEMA,
    )
    return True


async def async_setup_entry(hass: HomeAssistant, entry: PixooPalConfigEntry) -> bool:
    """Set up PixooPal from a config entry."""

    client = PixooPalClient(async_get_clientsession(hass), entry.data[CONF_BASE_URL])
    coordinator = PixooPalCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform(platform) for platform in PLATFORMS]
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PixooPalConfigEntry) -> bool:
    """Unload a PixooPal config entry."""

    return await hass.config_entries.async_unload_platforms(
        entry, [Platform(platform) for platform in PLATFORMS]
    )
