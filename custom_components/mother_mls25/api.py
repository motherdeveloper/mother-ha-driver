"""Thin CoAP/CBOR client for the Mother MLS25 driver.

The MLS25 firmware exposes a CoAP server (UDP/5683) with CBOR payloads:

    GET  /led/<ch>            -> {"lvl": 0..100}
    POST /led/<ch>            <- {"lvl": 0..100, "rate"?: 0..100}
    POST /led/<ch>/on | /off

Levels are percentages (0..100). ``rate`` is a fade speed (0..100, higher is
faster). The warm/daylight colour shift is handled in the spot itself based on
the level, so there is nothing colour-related to send.
"""

from __future__ import annotations

import asyncio

import cbor2
from aiocoap import Code, Context, Message

from .const import COAP_TIMEOUT, CONTENT_FORMAT_CBOR, DEFAULT_PORT


class MLS25Error(Exception):
    """Raised when the driver cannot be reached or returns an error."""


class MLS25Client:
    """Talks CoAP to a single MLS25 driver."""

    def __init__(self, host: str, port: int = DEFAULT_PORT) -> None:
        self._host = host
        self._port = port
        self._ctx: Context | None = None
        self._ctx_lock = asyncio.Lock()

    @property
    def host(self) -> str:
        return self._host

    def set_host(self, host: str) -> None:
        """Update the host (e.g. after the device gets a new DHCP lease)."""
        self._host = host

    async def _context(self) -> Context:
        if self._ctx is None:
            async with self._ctx_lock:
                if self._ctx is None:
                    self._ctx = await Context.create_client_context()
        return self._ctx

    def _uri(self, path: str) -> str:
        return f"coap://{self._host}:{self._port}/{path}"

    async def _request(self, msg: Message) -> Message:
        ctx = await self._context()
        try:
            return await asyncio.wait_for(ctx.request(msg).response, COAP_TIMEOUT)
        except asyncio.TimeoutError as err:
            raise MLS25Error(f"Timeout talking to {self._host}") from err
        except Exception as err:  # noqa: BLE001 - surface any aiocoap failure uniformly
            raise MLS25Error(f"CoAP error talking to {self._host}: {err}") from err

    async def get_level(self, channel: int) -> int:
        """Return the current output level (0..100) of a channel."""
        msg = Message(code=Code.GET, uri=self._uri(f"led/{channel}"))
        resp = await self._request(msg)
        data = cbor2.loads(resp.payload) if resp.payload else {}
        return int(data.get("lvl", 0))

    async def set_level(
        self, channel: int, level: int, rate: int | None = None
    ) -> None:
        """Set a channel target level (0..100), optionally with a fade rate."""
        payload: dict[str, int] = {"lvl": int(level)}
        if rate is not None:
            payload["rate"] = int(rate)
        msg = Message(
            code=Code.POST,
            uri=self._uri(f"led/{channel}"),
            payload=cbor2.dumps(payload),
        )
        msg.opt.content_format = CONTENT_FORMAT_CBOR
        await self._request(msg)

    async def set_onoff(self, channel: int, on: bool) -> None:
        """Turn a channel fully on (100%) or off."""
        path = f"led/{channel}/{'on' if on else 'off'}"
        msg = Message(code=Code.POST, uri=self._uri(path))
        await self._request(msg)

    async def close(self) -> None:
        if self._ctx is not None:
            await self._ctx.shutdown()
            self._ctx = None
