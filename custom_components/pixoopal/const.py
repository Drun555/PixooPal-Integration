"""Constants for the PixooPal integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "pixoopal"
DEFAULT_PORT: Final = 3000
DEFAULT_SCAN_INTERVAL_SECONDS: Final = 15

CONF_BASE_URL: Final = "base_url"
CONF_HOST: Final = "host"
CONF_PORT: Final = "port"

PLATFORMS: Final = ["camera", "light", "notify", "select"]

PROXY_URL: Final = "/api/pixoopal"

MANUFACTURER: Final = "Divoom"
MODEL: Final = "Pixoo via PixooPal"
