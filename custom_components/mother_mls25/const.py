"""Constants for the Mother MLS25 integration."""

from __future__ import annotations

DOMAIN = "mother_mls25"

DEFAULT_PORT = 5683
NUM_CHANNELS = 2
SCAN_INTERVAL_SECONDS = 10
COAP_TIMEOUT = 8
CONTENT_FORMAT_CBOR = 60

# Default fade speed sent when Home Assistant does not request a transition.
# None means "let the firmware use its own default fade".
DEFAULT_FADE_RATE: int | None = None

# Channel types. v1 only knows "light"; future firmware will report the actual
# type per channel (e.g. air-quality / motion sensor) and new platforms can be
# added without touching the existing ones.
CHANNEL_TYPE_LIGHT = "light"

MANUFACTURER = "Mother"
MODEL = "PoE driver"
