"""Config flow for the Mother MLS25 integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_HOST
from homeassistant.helpers.device_registry import format_mac
from homeassistant.helpers.service_info.dhcp import DhcpServiceInfo
from homeassistant.helpers.service_info.zeroconf import ZeroconfServiceInfo

from .api import MLS25Client, MLS25Error
from .const import DOMAIN, MODEL


class MLS25ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Mother MLS25."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._title: str = MODEL

    async def _async_test(self, host: str) -> None:
        """Raise MLS25Error if the driver is not reachable."""
        client = MLS25Client(host)
        try:
            await client.get_level(0)
        finally:
            await client.close()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manual setup: the user types the driver's IP address."""
        errors: dict[str, str] = {}
        if user_input is not None:
            host = user_input[CONF_HOST]
            try:
                await self._async_test(host)
            except MLS25Error:
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(host)
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"{MODEL} ({host})", data={CONF_HOST: host}
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {vol.Required(CONF_HOST, default=self._host or ""): str}
            ),
            errors=errors,
        )

    async def async_step_dhcp(
        self, discovery_info: DhcpServiceInfo
    ) -> ConfigFlowResult:
        """Auto-discovery via DHCP (hostname mls25-*). Yields the MAC."""
        await self.async_set_unique_id(format_mac(discovery_info.macaddress))
        self._abort_if_unique_id_configured(updates={CONF_HOST: discovery_info.ip})

        self._host = discovery_info.ip
        self._title = discovery_info.hostname or f"{MODEL} ({discovery_info.ip})"
        self.context["title_placeholders"] = {"name": self._title}
        return await self.async_step_discovery_confirm()

    async def async_step_zeroconf(
        self, discovery_info: ZeroconfServiceInfo
    ) -> ConfigFlowResult:
        """Auto-discovery via mDNS (_mother-life._udp)."""
        host = str(discovery_info.ip_address)
        # Don't open a second flow if this driver is already set up (e.g. it was
        # also found via DHCP, the preferred MAC-based path).
        self._async_abort_entries_match({CONF_HOST: host})
        # The mDNS instance name is shared across all units, so key on the host.
        await self.async_set_unique_id(f"mls25-{host}")
        self._abort_if_unique_id_configured(updates={CONF_HOST: host})

        self._host = host
        self._title = f"{MODEL} ({host})"
        self.context["title_placeholders"] = {"name": self._title}
        return await self.async_step_discovery_confirm()

    async def async_step_discovery_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm adding a discovered driver."""
        assert self._host is not None
        if user_input is not None:
            try:
                await self._async_test(self._host)
            except MLS25Error:
                return self.async_abort(reason="cannot_connect")
            return self.async_create_entry(
                title=self._title, data={CONF_HOST: self._host}
            )

        return self.async_show_form(
            step_id="discovery_confirm",
            description_placeholders={"name": self._title},
        )
