"""Config flow for PixooPal."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .client import PixooPalCannotConnect, PixooPalError, normalize_base_url, PixooPalClient
from .const import CONF_BASE_URL, CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN


class PixooPalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a PixooPal config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                normalized = normalize_base_url(
                    str(user_input[CONF_HOST]), user_input.get(CONF_PORT)
                )
            except (TypeError, ValueError):
                errors["base"] = "invalid_host"
            else:
                await self.async_set_unique_id(normalized.base_url)
                self._abort_if_unique_id_configured()

                client = PixooPalClient(
                    async_get_clientsession(self.hass), normalized.base_url
                )
                try:
                    await client.status()
                except PixooPalCannotConnect:
                    errors["base"] = "cannot_connect"
                except PixooPalError:
                    errors["base"] = "unknown"
                else:
                    return self.async_create_entry(
                        title=f"PixooPal ({normalized.host}:{normalized.port})",
                        data={
                            CONF_BASE_URL: normalized.base_url,
                            CONF_HOST: normalized.host,
                            CONF_PORT: normalized.port,
                        },
                    )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_HOST): str,
                    vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
                }
            ),
            errors=errors,
        )
