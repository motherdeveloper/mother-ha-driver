"""Polling coordinator for the Mother MLS25 driver.

The firmware has no push/observe, so we poll each channel's level on an
interval. Data shape:

    {"channels": {0: {"type": "light", "level": 60}, 1: {...}}}

Keeping a ``type`` per channel makes it cheap to add other channel types
(sensors, ...) later: a new platform just picks the channels whose type it
handles.
"""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import MLS25Client, MLS25Error
from .const import CHANNEL_TYPE_LIGHT, DOMAIN, NUM_CHANNELS, SCAN_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)

type ChannelData = dict[str, object]
type MLS25Data = dict[str, dict[int, ChannelData]]


class MLS25Coordinator(DataUpdateCoordinator[MLS25Data]):
    """Polls all channels of one MLS25 driver."""

    def __init__(
        self, hass: HomeAssistant, entry: ConfigEntry, client: MLS25Client
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=SCAN_INTERVAL_SECONDS),
        )
        self.client = client
        self.entry = entry

    async def _async_update_data(self) -> MLS25Data:
        channels: dict[int, ChannelData] = {}
        try:
            for ch in range(NUM_CHANNELS):
                level = await self.client.get_level(ch)
                channels[ch] = {"type": CHANNEL_TYPE_LIGHT, "level": level}
        except MLS25Error as err:
            raise UpdateFailed(str(err)) from err
        return {"channels": channels}
