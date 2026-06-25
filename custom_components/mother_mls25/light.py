"""Light platform for the Mother MLS25 driver."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_TRANSITION,
    ColorMode,
    LightEntity,
    LightEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CHANNEL_TYPE_LIGHT, DEFAULT_FADE_RATE, DOMAIN, MANUFACTURER, MODEL
from .coordinator import MLS25Coordinator

if TYPE_CHECKING:
    from . import MLS25ConfigEntry


def _ha_to_pct(brightness: int) -> int:
    """Home Assistant brightness (0..255) -> firmware level (0..100)."""
    return round(brightness / 255 * 100)


def _pct_to_ha(pct: int) -> int:
    """Firmware level (0..100) -> Home Assistant brightness (0..255)."""
    return round(pct / 100 * 255)


def _rate_from_kwargs(kwargs: dict[str, Any]) -> int | None:
    """Map a requested transition (seconds) to a firmware fade rate.

    The firmware ``rate`` is a fade *speed* (0..100, higher = faster), not a
    duration, so this is an approximation: ~40 is fast, ~5 is slow.
    """
    transition = kwargs.get(ATTR_TRANSITION)
    if transition is None:
        return DEFAULT_FADE_RATE
    return max(1, min(100, round(40 / max(float(transition), 0.4))))


async def async_setup_entry(
    hass: HomeAssistant,
    entry: MLS25ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the light entities for a config entry."""
    coordinator = entry.runtime_data
    async_add_entities(
        MLS25Light(coordinator, entry, channel)
        for channel, info in coordinator.data["channels"].items()
        if info["type"] == CHANNEL_TYPE_LIGHT
    )


class MLS25Light(CoordinatorEntity[MLS25Coordinator], LightEntity):
    """A single dimmable output channel of an MLS25 driver."""

    _attr_has_entity_name = True
    _attr_color_mode = ColorMode.BRIGHTNESS
    _attr_supported_color_modes = {ColorMode.BRIGHTNESS}
    _attr_supported_features = LightEntityFeature.TRANSITION

    def __init__(
        self, coordinator: MLS25Coordinator, entry: MLS25ConfigEntry, channel: int
    ) -> None:
        super().__init__(coordinator)
        self._channel = channel
        device_id = entry.unique_id or entry.entry_id
        self._attr_unique_id = f"{device_id}_led_{channel}"
        self._attr_name = f"Channel {channel}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=entry.title,
            manufacturer=MANUFACTURER,
            model=MODEL,
        )

    @property
    def _level(self) -> int:
        return int(self.coordinator.data["channels"][self._channel]["level"])

    @property
    def is_on(self) -> bool:
        return self._level > 0

    @property
    def brightness(self) -> int | None:
        return _pct_to_ha(self._level)

    async def async_turn_on(self, **kwargs: Any) -> None:
        rate = _rate_from_kwargs(kwargs)
        if ATTR_BRIGHTNESS in kwargs:
            level = max(1, _ha_to_pct(kwargs[ATTR_BRIGHTNESS]))
            await self.coordinator.client.set_level(self._channel, level, rate)
        elif rate is not None:
            await self.coordinator.client.set_level(self._channel, 100, rate)
        else:
            await self.coordinator.client.set_onoff(self._channel, True)
        await self.coordinator.async_request_refresh()

    async def async_turn_off(self, **kwargs: Any) -> None:
        rate = _rate_from_kwargs(kwargs)
        if rate is not None:
            await self.coordinator.client.set_level(self._channel, 0, rate)
        else:
            await self.coordinator.client.set_onoff(self._channel, False)
        await self.coordinator.async_request_refresh()
