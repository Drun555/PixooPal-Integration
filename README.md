# PixooPal Integration

Home Assistant integration for PixooPal WebUI.

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=yourname&repository=PixooPal-Integration&category=integration)

## Install

Add this repository to HACS as **Integration**, install it, restart Home Assistant, then add **PixooPal** from **Settings -> Devices & services**.

Default PixooPal WebUI port: `3000`

## Entities

- `camera.pixoopal_preview`
- `select.pixoopal_clockface`
- `light.pixoopal_display`
- `notify.pixoopal_notify`

## Notify With Beep

```yaml
action: pixoopal.notify
data:
  message: "Door opened"
  beep: true
```
