"""The Mother MLS25 integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, Platform
from homeassistant.core import HomeAssistant

from .api import MLS25Client
from .const import DOMAIN
from .coordinator import MLS25Coordinator
from .http_api import async_register_http_api

PLATFORMS: list[Platform] = [Platform.LIGHT]

type MLS25ConfigEntry = ConfigEntry[MLS25Coordinator]


async def async_setup_entry(hass: HomeAssistant, entry: MLS25ConfigEntry) -> bool:
    """Set up Mother MLS25 from a config entry."""
    client = MLS25Client(entry.data[CONF_HOST])
    coordinator = MLS25Coordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    # Register the plain-text HTTP endpoints once (for Loxone and other
    # HTTP-only controllers). See http_api.py and docs/loxone.md.
    hass.data.setdefault(DOMAIN, {})
    if not hass.data[DOMAIN].get("http_registered"):
        async_register_http_api(hass)
        hass.data[DOMAIN]["http_registered"] = True

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: MLS25ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        await entry.runtime_data.client.close()
    return unload_ok
