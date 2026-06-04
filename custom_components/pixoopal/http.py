"""HTTP proxy for PixooPal card requests."""

from __future__ import annotations

from aiohttp import FormData, web

from homeassistant.components.http import HomeAssistantView
from homeassistant.helpers.template import Template

from .const import DOMAIN, PROXY_URL


class PixooPalEntriesView(HomeAssistantView):
    """Expose PixooPal config entries for the Lovelace card."""

    url = f"{PROXY_URL}/entries"
    name = "api:pixoopal:entries"
    requires_auth = True

    async def get(self, request: web.Request) -> web.Response:
        """Return configured PixooPal entries."""

        hass = request.app["hass"]
        entries = [
            {
                "entry_id": entry.entry_id,
                "title": entry.title,
            }
            for entry in hass.config_entries.async_entries(DOMAIN)
        ]

        return web.json_response({"entries": entries})


class PixooPalProxyView(HomeAssistantView):
    """Authenticated PixooPal API proxy for the Lovelace card."""

    url = f"{PROXY_URL}/{{entry_id}}/{{tail:.*}}"
    name = "api:pixoopal:proxy"
    requires_auth = True

    async def get(self, request: web.Request, entry_id: str, tail: str) -> web.Response:
        """Proxy GET requests."""

        return await self._proxy(request, entry_id, tail)

    async def post(self, request: web.Request, entry_id: str, tail: str) -> web.Response:
        """Proxy POST requests."""

        return await self._proxy(request, entry_id, tail)

    async def _proxy(self, request: web.Request, entry_id: str, tail: str) -> web.Response:
        hass = request.app["hass"]
        entry = hass.config_entries.async_get_entry(entry_id)

        if entry is None or entry.domain != DOMAIN:
            raise web.HTTPNotFound(text="PixooPal entry was not found")

        coordinator = entry.runtime_data
        path = f"/{tail}"
        if request.query_string:
            path = f"{path}?{request.query_string}"

        headers: dict[str, str] = {}
        if content_type := request.headers.get("content-type"):
            headers["content-type"] = content_type

        data = None
        json_payload = None
        if request.method != "GET":
            if request.content_type == "application/json":
                json_payload = await request.json()
            elif request.content_type.startswith("multipart/"):
                form = FormData()
                reader = await request.multipart()
                async for part in reader:
                    field_name = part.name or ""
                    if part.filename:
                        form.add_field(
                            field_name,
                            await part.read(),
                            filename=part.filename,
                            content_type=part.headers.get("content-type", "application/octet-stream"),
                        )
                    else:
                        form.add_field(field_name, await part.text())
                data = form
                headers.pop("content-type", None)
            else:
                data = await request.read()

        response = await coordinator.client.proxy(
            request.method,
            path,
            headers=headers or None,
            data=data,
            json=json_payload,
        )
        async with response:
            body = await response.read()
            proxied_headers = {
                key: value
                for key, value in response.headers.items()
                if key.lower() in {"content-type", "cache-control"}
            }
            return web.Response(body=body, status=response.status, headers=proxied_headers)


class PixooPalTemplateRenderView(HomeAssistantView):
    """Render Home Assistant Jinja templates for a connected PixooPal Core."""

    url = f"{PROXY_URL}/{{entry_id}}/template/render"
    name = "api:pixoopal:template_render"
    requires_auth = True

    async def post(self, request: web.Request, entry_id: str) -> web.Response:
        """Render a template string inside Home Assistant."""

        hass = request.app["hass"]
        entry = hass.config_entries.async_get_entry(entry_id)

        if entry is None or entry.domain != DOMAIN:
            raise web.HTTPNotFound(text="PixooPal entry was not found")

        try:
            payload = await request.json()
        except ValueError as err:
            raise web.HTTPBadRequest(text="Request body must be JSON") from err

        template_string = payload.get("template") if isinstance(payload, dict) else None
        variables = payload.get("variables", {}) if isinstance(payload, dict) else {}

        if not isinstance(template_string, str):
            raise web.HTTPBadRequest(text="Template is required")

        if not isinstance(variables, dict):
            variables = {}

        try:
            template = Template(template_string, hass)
            result = template.async_render(variables=variables, parse_result=False)
        except Exception as err:
            return web.json_response({"ok": False, "message": str(err)}, status=500)

        return web.json_response({"ok": True, "result": str(result)})
