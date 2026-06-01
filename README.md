# PixooPal Integration

Home Assistant integration for PixooPal WebUI. It provides next entities to have fun with:
- `camera.pixoopal_preview`
- `select.pixoopal_clockface`
- `light.pixoopal_display`
- `notify.pixoopal_notify`

## Install

Add this repository to HACS as **Integration**, install it, restart Home Assistant, then add **PixooPal** from **Settings -> Devices & services**.



Integration:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Drun555&repository=PixooPal-Integration&category=integration)


You should also install [this shiny useful custom card](https://github.com/Drun555/PixooPal-Card) that will render custom inputs of your clockfaces for you:

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Drun555&repository=PixooPal-Card&category=plugin)

## Notify service usage:

```yaml
action: pixoopal.notify
data:
  message: "Door opened ❤️"
  beep: true
```
