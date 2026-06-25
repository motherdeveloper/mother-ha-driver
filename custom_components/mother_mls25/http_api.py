"""Plain-text HTTP endpoints for non-HA controllers (Loxone, ...).

These are registered inside Home Assistant so that controllers which speak HTTP
but not CoAP -- e.g. a Loxone Miniserver -- can drive the MLS25 lights. HA does
the HTTP<->CoAP translation; this makes the HA-on-a-Pi box a universal hub.

Responses are plain text so a Loxone Virtual Input parses them without any JSON
or token handling:

    GET /api/mls25/level?ch=0[&host=<ip>]                  -> "60"
    GET /api/mls25/set?ch=0&level=60[&rate=20][&host=<ip>] -> "OK"
    GET /api/mls25/on?ch=0[&host=<ip>]                     -> "OK"
    GET /api/mls25/off?ch=0[&host=<ip>]                    -> "OK"

`host` selects which driver when several are configured; if omitted, the first
configured driver is used. No authentication is required (trusted-LAN only,
matching the driver itself).
"""

from __future__ import annotations

from aiohttp import web

from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant

from .api import MLS25Client, MLS25Error
from .const import DOMAIN, NUM_CHANNELS


def _to_float(value: str) -> float:
    """Parse a number that may use a decimal comma (e.g. Loxone '48,0')."""
    return float(value.strip().replace(",", "."))


def _find_client(hass: HomeAssistant, host: str | None) -> MLS25Client | None:
    """Return the CoAP client for `host`, or the first configured one."""
    for entry in hass.config_entries.async_entries(DOMAIN):
        coordinator = getattr(entry, "runtime_data", None)
        if coordinator is None:
            continue
        client: MLS25Client = coordinator.client
        if host is None or client.host == host:
            return client
    return None


class MLS25HttpView(HomeAssistantView):
    """Plain-text control/readout endpoint for external controllers."""

    url = "/api/mls25/{action}"
    name = "api:mls25"
    requires_auth = False

    async def get(self, request: web.Request, action: str) -> web.Response:
        hass: HomeAssistant = request.app["hass"]
        query = request.query

        client = _find_client(hass, query.get("host"))
        if client is None:
            return web.Response(text="ERR no driver", status=404)

        try:
            ch = int(query.get("ch", "0"))
        except ValueError:
            return web.Response(text="ERR bad ch", status=400)
        if not 0 <= ch < NUM_CHANNELS:
            return web.Response(text="ERR bad ch", status=400)

        try:
            if action == "level":
                return web.Response(text=str(await client.get_level(ch)))

            if action == "set":
                # Accept "48", "48.0" and "48,0" (Loxone <v> may send decimals
                # or a locale comma).
                level = max(0, min(100, round(_to_float(query.get("level", "0")))))
                rate_raw = query.get("rate")
                rate = round(_to_float(rate_raw)) if rate_raw is not None else None
                await client.set_level(ch, level, rate)
                return web.Response(text="OK")

            if action in ("on", "off"):
                await client.set_onoff(ch, action == "on")
                return web.Response(text="OK")
        except ValueError:
            return web.Response(text="ERR bad value", status=400)
        except MLS25Error as err:
            return web.Response(text=f"ERR {err}", status=502)

        return web.Response(text="ERR unknown action", status=404)


def async_register_http_api(hass: HomeAssistant) -> None:
    """Register the plain-text HTTP view (once)."""
    hass.http.register_view(MLS25HttpView())
