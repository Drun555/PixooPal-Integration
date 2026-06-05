"""Config flow for PixooPal."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.service_info.hassio import HassioServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .client import (
    PixooPalCannotConnect,
    PixooPalClient,
    PixooPalConfig,
    PixooPalError,
    normalize_base_url,
)
from .const import CONF_BASE_URL, CONF_HOST, CONF_PORT, DEFAULT_PORT, DOMAIN

DISCOVERED_CONFIG_KEY = "discovered_config"


class PixooPalConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a PixooPal config flow."""

    VERSION = 1

    _discovered_config: PixooPalConfig | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""

        errors: dict[str, str] = {}
        default_config = self._get_discovered_config()

        if user_input is not None:
            try:
                normalized = normalize_base_url(
                    str(user_input[CONF_HOST]), user_input.get(CONF_PORT)
                )
            except (TypeError, ValueError):
                errors["base"] = "invalid_host"
            else:
                try:
                    await self._async_confirm_instance(normalized, use_discovery=False)
                except PixooPalCannotConnect:
                    errors["base"] = "cannot_connect"
                except PixooPalError:
                    errors["base"] = "unknown"
                else:
                    return self._async_create_pixoopal_entry(normalized)

        return self.async_show_form(
            step_id="user",
            data_schema=self._user_schema(default_config),
            errors=errors,
        )

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle PixooPal discovered through zeroconf."""

        try:
            normalized = normalize_base_url(discovery_info.host, discovery_info.port)
            discovery = await self._async_confirm_instance(normalized, use_discovery=True)
        except (PixooPalCannotConnect, PixooPalError, TypeError, ValueError):
            return self.async_abort(reason="cannot_connect")

        self._discovered_config = normalized
        self._set_discovered_config(normalized)
        self.context["title_placeholders"] = {
            "name": str(discovery.get("name") or discovery_info.name or "PixooPal"),
            "host": normalized.host,
            "port": str(normalized.port),
        }
        return await self.async_step_zeroconf_confirm()

    async def async_step_hassio(
        self, discovery_info: HassioServiceInfo
    ) -> config_entries.ConfigFlowResult:
        """Handle PixooPal discovered through a Home Assistant add-on."""

        try:
            config = discovery_info.config
            normalized = normalize_base_url(str(config[CONF_HOST]), config[CONF_PORT])
            discovery = await self._async_confirm_instance(normalized, use_discovery=True)
        except (
            KeyError,
            PixooPalCannotConnect,
            PixooPalError,
            TypeError,
            ValueError,
        ):
            return self.async_abort(reason="cannot_connect")

        self._discovered_config = normalized
        self._set_discovered_config(normalized)
        self.context["title_placeholders"] = {
            "name": str(discovery.get("name") or discovery_info.name or "PixooPal"),
            "host": normalized.host,
            "port": str(normalized.port),
        }
        return await self.async_step_hassio_confirm()

    async def async_step_zeroconf_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm a discovered PixooPal instance."""

        return await self._async_confirm_discovered("zeroconf_confirm", user_input)

    async def async_step_hassio_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Confirm a PixooPal instance discovered through a Home Assistant add-on."""

        return await self._async_confirm_discovered("hassio_confirm", user_input)

    async def _async_confirm_discovered(
        self, step_id: str, user_input: dict[str, Any] | None
    ) -> config_entries.ConfigFlowResult:
        """Confirm a discovered PixooPal instance."""

        if self._discovered_config is None:
            return self.async_abort(reason="cannot_connect")

        if user_input is not None:
            return self._async_create_pixoopal_entry(self._discovered_config)

        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({}),
            description_placeholders={
                "host": self._discovered_config.host,
                "port": str(self._discovered_config.port),
            },
        )

    async def _async_confirm_instance(
        self, config: PixooPalConfig, *, use_discovery: bool
    ) -> dict[str, Any]:
        """Confirm that a normalized URL points at a PixooPal instance."""

        await self.async_set_unique_id(config.base_url)
        self._abort_if_unique_id_configured()

        client = PixooPalClient(async_get_clientsession(self.hass), config.base_url)
        return await (client.discovery() if use_discovery else client.status())

    def _async_create_pixoopal_entry(
        self, config: PixooPalConfig
    ) -> config_entries.ConfigFlowResult:
        """Create a PixooPal config entry."""

        return self.async_create_entry(
            title=f"PixooPal ({config.host}:{config.port})",
            data={
                CONF_BASE_URL: config.base_url,
                CONF_HOST: config.host,
                CONF_PORT: config.port,
            },
        )

    def _user_schema(self, default_config: PixooPalConfig | None) -> vol.Schema:
        """Return the manual setup form schema with discovered defaults when available."""

        host_field = (
            vol.Required(CONF_HOST, default=default_config.host)
            if default_config
            else vol.Required(CONF_HOST)
        )

        return vol.Schema(
            {
                host_field: str,
                vol.Optional(
                    CONF_PORT,
                    default=default_config.port if default_config else DEFAULT_PORT,
                ): int,
            }
        )

    def _get_discovered_config(self) -> PixooPalConfig | None:
        """Return the latest auto-discovered PixooPal config for form defaults."""

        data = self.hass.data.get(DOMAIN)
        if not isinstance(data, dict):
            return None

        config = data.get(DISCOVERED_CONFIG_KEY)
        return config if isinstance(config, PixooPalConfig) else None

    def _set_discovered_config(self, config: PixooPalConfig) -> None:
        """Remember the latest auto-discovered PixooPal config for manual setup."""

        self.hass.data.setdefault(DOMAIN, {})[DISCOVERED_CONFIG_KEY] = config
