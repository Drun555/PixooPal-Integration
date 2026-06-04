"""Async client for the PixooPal WebUI API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from urllib.parse import urlparse

from aiohttp import ClientError, ClientResponse, ClientSession, ClientTimeout, FormData

from .const import DEFAULT_PORT


class PixooPalError(Exception):
    """Base PixooPal API error."""


class PixooPalCannotConnect(PixooPalError):
    """Raised when PixooPal cannot be reached."""


class PixooPalApiError(PixooPalError):
    """Raised when PixooPal returns an API error."""


@dataclass(frozen=True)
class PixooPalConfig:
    """Normalized PixooPal connection config."""

    base_url: str
    host: str
    port: int


def normalize_base_url(host: str, port: int | str | None = None) -> PixooPalConfig:
    """Normalize user input to a PixooPal base URL."""

    value = host.strip()
    if not value:
        raise ValueError("Host is required")

    if "://" not in value:
        value = f"http://{value}"

    parsed = urlparse(value)
    scheme = parsed.scheme or "http"
    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Host is invalid")

    parsed_port = parsed.port
    final_port = int(port) if port not in (None, "") else parsed_port or DEFAULT_PORT
    if final_port <= 0 or final_port > 65535:
        raise ValueError("Port is invalid")

    netloc = f"{hostname}:{final_port}"
    return PixooPalConfig(base_url=f"{scheme}://{netloc}", host=hostname, port=final_port)


class PixooPalClient:
    """Small typed wrapper around the PixooPal HTTP API."""

    def __init__(self, session: ClientSession, base_url: str) -> None:
        """Initialize the client."""

        self._session = session
        self.base_url = base_url.rstrip("/")
        self._timeout = ClientTimeout(total=10)

    def url(self, path: str) -> str:
        """Return an absolute PixooPal URL."""

        return f"{self.base_url}/{path.lstrip('/')}"

    async def status(self) -> dict[str, Any]:
        """Fetch PixooPal status."""

        return await self._request_json("GET", "/api/v1/status")

    async def discovery(self) -> dict[str, Any]:
        """Fetch PixooPal discovery metadata."""

        return await self._request_json("GET", "/api/v1/discovery")

    async def pixoo(self) -> dict[str, Any]:
        """Fetch Pixoo device state through PixooPal."""

        return await self._request_json("GET", "/api/pixoo")

    async def clockfaces(self) -> dict[str, Any]:
        """Fetch clockface list and active clockface."""

        return await self._request_json("GET", "/api/v1/clockfaces")

    async def control(self) -> dict[str, Any]:
        """Fetch PixooPal control state."""

        return await self._request_json("GET", "/api/v1/control")

    async def set_pixoo_pal_paused(self, paused: bool) -> dict[str, Any]:
        """Pause or resume PixooPal."""

        return await self._request_json(
            "POST", "/api/v1/control", json={"pixooPalOff": paused}
        )

    async def set_clockface(self, clockface_id: str) -> dict[str, Any]:
        """Set the active clockface."""

        return await self._request_json(
            "POST", "/api/v1/clockfaces/current", json={"id": clockface_id}
        )

    async def set_brightness(self, value: int) -> dict[str, Any]:
        """Set Pixoo brightness in the 0..100 range."""

        return await self._request_json(
            "POST", "/api/pixoo", json={"action": "brightness", "value": value}
        )

    async def set_screen(self, on: bool) -> dict[str, Any]:
        """Turn Pixoo screen on or off."""

        return await self._request_json("POST", "/api/pixoo", json={"action": "screen", "on": on})

    async def submit_input(self, input_id: str, value: str) -> dict[str, Any]:
        """Submit a JSON clockface input value."""

        return await self._request_json(
            "POST", "/api/v1/clockfaces/input", json={"inputId": input_id, "value": value}
        )

    async def submit_file_input(
        self, input_id: str, filename: str, content_type: str, data: bytes
    ) -> dict[str, Any]:
        """Submit a multipart clockface file input."""

        form = FormData()
        form.add_field("inputId", input_id)
        form.add_field("value", data, filename=filename, content_type=content_type)
        return await self._request_json("POST", "/api/v1/clockfaces/input", data=form)

    async def notify(self, message: str, beep: bool = False) -> dict[str, Any]:
        """Show a PixooPal notification overlay."""

        return await self._request_json(
            "POST", "/api/v1/notify", json={"message": message, "beep": beep}
        )

    async def home_assistant_handshake(
        self, entry_id: str, render_path: str, render_url: str | None = None
    ) -> dict[str, Any]:
        """Register Home Assistant template rendering with PixooPal."""

        payload: dict[str, Any] = {
            "entryId": entry_id,
            "renderPath": render_path,
        }
        if render_url:
            payload["renderUrl"] = render_url

        return await self._request_json(
            "POST", "/api/v1/home-assistant/handshake", json=payload
        )

    async def camera_image(self) -> bytes | None:
        """Fetch a still JPEG preview if PixooPal has one."""

        try:
            response = await self._request("GET", "/api/v1/preview.jpg")
        except PixooPalError:
            return None

        async with response:
            return await response.read()

    async def proxy(
        self,
        method: str,
        path: str,
        *,
        headers: dict[str, str] | None = None,
        data: Any = None,
        json: Any = None,
    ) -> ClientResponse:
        """Proxy an arbitrary request to PixooPal."""

        return await self._request(method, path, headers=headers, data=data, json=json)

    async def _request_json(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        response = await self._request(method, path, **kwargs)
        async with response:
            body = await response.json(content_type=None)
            if isinstance(body, dict) and body.get("ok") is False:
                raise PixooPalApiError(str(body.get("message") or "PixooPal API error"))
            if not isinstance(body, dict):
                raise PixooPalApiError("PixooPal returned a non-object JSON response")
            return body

    async def _request(self, method: str, path: str, **kwargs: Any) -> ClientResponse:
        try:
            response = await self._session.request(
                method, self.url(path), timeout=self._timeout, **kwargs
            )
        except (ClientError, TimeoutError) as err:
            raise PixooPalCannotConnect(str(err)) from err

        if response.status >= 400:
            body = await response.text()
            response.release()
            raise PixooPalApiError(f"PixooPal returned HTTP {response.status}: {body}")

        return response
