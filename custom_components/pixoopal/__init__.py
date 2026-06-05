"""PixooPal Home Assistant integration."""

from __future__ import annotations

import asyncio
from contextlib import suppress
import logging
import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.network import NoURLAvailableError, get_url

from .client import PixooPalClient, PixooPalError
from .const import CONF_BASE_URL, DOMAIN, LEGACY_PLATFORMS_FOR_UNLOAD, PLATFORMS
from .coordinator import PixooPalCoordinator
from .http import PixooPalEntriesView, PixooPalProxyView, PixooPalTemplateRenderView

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

_LOGGER = logging.getLogger(__name__)
TEMPLATE_HANDSHAKE_INTERVAL_SECONDS = 60


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration-level HTTP resources."""

    hass.http.register_view(PixooPalEntriesView)
    hass.http.register_view(PixooPalProxyView)
    hass.http.register_view(PixooPalTemplateRenderView)

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

        try:
            await coordinator.client.notify(text, call.data[ATTR_BEEP])
        except PixooPalError as err:
            raise HomeAssistantError(f"PixooPal is unavailable: {err}") from err

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
    handshake_task = hass.async_create_task(
        _async_home_assistant_template_handshake_loop(entry, coordinator)
    )
    entry.async_on_unload(handshake_task.cancel)
    await hass.config_entries.async_forward_entry_setups(
        entry, [Platform(platform) for platform in PLATFORMS]
    )
    return True


async def async_unload_entry(hass: HomeAssistant, entry: PixooPalConfigEntry) -> bool:
    """Unload a PixooPal config entry."""

    return await hass.config_entries.async_unload_platforms(
        entry,
        [
            Platform(platform)
            for platform in [*PLATFORMS, *LEGACY_PLATFORMS_FOR_UNLOAD]
        ],
    )


async def _async_register_home_assistant_template_render(
    entry: PixooPalConfigEntry, coordinator: PixooPalCoordinator
) -> None:
    """Tell PixooPal Core where Home Assistant templates can be rendered."""

    render_path = f"/api/pixoopal/{entry.entry_id}/template/render"
    render_url = _get_home_assistant_render_url(coordinator.hass, render_path)

    try:
        await coordinator.client.home_assistant_handshake(
            entry.entry_id,
            render_path,
            render_url,
            coordinator.template_render_token,
        )
    except PixooPalError as err:
        _LOGGER.warning("Could not register Home Assistant template rendering with PixooPal: %s", err)


async def _async_home_assistant_template_handshake_loop(
    entry: PixooPalConfigEntry, coordinator: PixooPalCoordinator
) -> None:
    """Keep Home Assistant template rendering registered with PixooPal Core."""

    with suppress(asyncio.CancelledError):
        while True:
            await _async_register_home_assistant_template_render(entry, coordinator)
            await asyncio.sleep(TEMPLATE_HANDSHAKE_INTERVAL_SECONDS)


def _get_home_assistant_render_url(hass: HomeAssistant, render_path: str) -> str | None:
    """Return an absolute Home Assistant URL for PixooPal Core to call back."""

    try:
        base_url = get_url(
            hass,
            allow_cloud=False,
            allow_external=True,
            allow_internal=True,
            prefer_external=False,
        )
    except NoURLAvailableError:
        return None

    return f"{base_url.rstrip('/')}{render_path}"
