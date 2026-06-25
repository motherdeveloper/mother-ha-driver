#!/usr/bin/env python3
"""
Proof-of-concept CoAP client for the Mother MLS25 PoE+ LED driver.

Talks to the MLS25 firmware over CoAP/UDP (port 5683) with CBOR payloads, so we
can validate the whole chain (discover -> control -> read back) against a real
board before building the Home Assistant integration.

Endpoints (see mother-mls25-zephyr-app-master/src/app_coap/led_res.c):
  GET  /led/<ch>            -> {"lvl": 0..100}
  POST /led/<ch>            <- {"lvl": 0..100, "rate"?: 0..100}
  POST /led/<ch>/on | /off

Channels are 0 and 1. Level is a 0..100 percentage. 'rate' is the fade speed
(0..100, higher = faster). The warm/daylight colour shift happens automatically
in the spot itself based on the level, so there is nothing colour-related to
send here.

Examples:
  python test_coap.py --discover
  python test_coap.py 192.168.1.50 --status
  python test_coap.py 192.168.1.50 -c 0 --level 60 --rate 20
  python test_coap.py 192.168.1.50 -c 1 --on
  python test_coap.py 192.168.1.50 --demo
"""

import argparse
import asyncio
import sys

import cbor2
from aiocoap import Code, Context, Message

PORT = 5683
NUM_CHANNELS = 2
CONTENT_FORMAT_CBOR = 60
REQUEST_TIMEOUT = 10  # seconds, guards against a stuck/unreachable device


# --------------------------------------------------------------------------- #
# CoAP helpers
# --------------------------------------------------------------------------- #

def _uri(host: str, path: str) -> str:
    return f"coap://{host}:{PORT}/{path}"


async def _request(ctx: Context, msg: Message) -> Message:
    """Send a request with a hard timeout and friendly errors."""
    try:
        return await asyncio.wait_for(ctx.request(msg).response, REQUEST_TIMEOUT)
    except asyncio.TimeoutError:
        raise SystemExit(
            "No response from the device. Check that the IP is correct, that "
            "you are on the same subnet, and that nothing is blocking UDP/5683."
        )


async def get_level(ctx: Context, host: str, ch: int) -> int:
    msg = Message(code=Code.GET, uri=_uri(host, f"led/{ch}"))
    resp = await _request(ctx, msg)
    data = cbor2.loads(resp.payload) if resp.payload else {}
    return data.get("lvl")


async def set_level(ctx: Context, host: str, ch: int, lvl: int, rate=None) -> str:
    payload = {"lvl": lvl}
    if rate is not None:
        payload["rate"] = rate
    msg = Message(code=Code.POST, uri=_uri(host, f"led/{ch}"),
                  payload=cbor2.dumps(payload))
    msg.opt.content_format = CONTENT_FORMAT_CBOR
    resp = await _request(ctx, msg)
    return str(resp.code)


async def set_onoff(ctx: Context, host: str, ch: int, on: bool) -> str:
    msg = Message(code=Code.POST, uri=_uri(host, f"led/{ch}/{'on' if on else 'off'}"))
    resp = await _request(ctx, msg)
    return str(resp.code)


# --------------------------------------------------------------------------- #
# Actions
# --------------------------------------------------------------------------- #

async def cmd_status(ctx: Context, host: str) -> None:
    print(f"Status of {host}:")
    for ch in range(NUM_CHANNELS):
        lvl = await get_level(ctx, host, ch)
        print(f"  channel {ch}: {lvl}%")


async def cmd_demo(ctx: Context, host: str, ch: int) -> None:
    print(f"Demo on {host} channel {ch} (watch the light)...")
    steps = [
        ("on (100%)", lambda: set_onoff(ctx, host, ch, True)),
        ("fade to 30% (slow)", lambda: set_level(ctx, host, ch, 30, rate=10)),
        ("fade to 100% (slow)", lambda: set_level(ctx, host, ch, 100, rate=10)),
        ("snap to 50% (no fade)", lambda: set_level(ctx, host, ch, 50, rate=0)),
        ("off", lambda: set_onoff(ctx, host, ch, False)),
    ]
    for label, action in steps:
        code = await action()
        print(f"  {label:<24} -> {code}")
        await asyncio.sleep(2)
    print("Demo done.")


# --------------------------------------------------------------------------- #
# mDNS discovery (optional, no device control)
# --------------------------------------------------------------------------- #

def discover(timeout: float = 4.0) -> None:
    """Browse for _mother-life._udp drivers on the LAN and print them."""
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except ImportError:
        raise SystemExit("Discovery needs 'zeroconf' (pip install zeroconf).")
    import time

    service_type = "_mother-life._udp.local."
    found: dict = {}

    class Listener(ServiceListener):
        def add_service(self, zc, type_, name):
            info = zc.get_service_info(type_, name)
            if info:
                found[name] = (info.parsed_scoped_addresses(), info.port, info.server)

        def update_service(self, zc, type_, name):
            self.add_service(zc, type_, name)

        def remove_service(self, zc, type_, name):
            pass

    zc = Zeroconf()
    print(f"Browsing {service_type} for {timeout:.0f}s ...")
    ServiceBrowser(zc, service_type, Listener())
    try:
        time.sleep(timeout)
    finally:
        zc.close()

    if not found:
        print("No drivers found. (Note: all units advertise the same mDNS name "
              "'MLS25', so multiple devices may merge into one entry.)")
        return
    for name, (addrs, port, server) in found.items():
        print(f"\n  {name}")
        print(f"    addresses: {', '.join(addrs)}")
        print(f"    port:      {port}")
        print(f"    server:    {server}")


# --------------------------------------------------------------------------- #
# Entry point
# --------------------------------------------------------------------------- #

async def run(args) -> None:
    ctx = await Context.create_client_context()
    try:
        if args.demo:
            await cmd_demo(ctx, args.host, args.channel)
        elif args.on:
            print(await set_onoff(ctx, args.host, args.channel, True))
        elif args.off:
            print(await set_onoff(ctx, args.host, args.channel, False))
        elif args.level is not None:
            print(await set_level(ctx, args.host, args.channel, args.level, args.rate))
        else:
            await cmd_status(ctx, args.host)
    finally:
        await ctx.shutdown()


def main() -> None:
    p = argparse.ArgumentParser(
        description="CoAP test client for the Mother MLS25 driver.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument("host", nargs="?", help="IP address or hostname of the driver")
    p.add_argument("--discover", action="store_true", help="find drivers via mDNS and exit")
    p.add_argument("-c", "--channel", type=int, default=0, choices=range(NUM_CHANNELS),
                   help="channel index (default 0)")
    p.add_argument("-l", "--level", type=int, help="set level 0..100")
    p.add_argument("--rate", type=int, help="fade rate 0..100 (optional)")
    p.add_argument("--on", action="store_true", help="turn channel on")
    p.add_argument("--off", action="store_true", help="turn channel off")
    p.add_argument("--status", action="store_true", help="read all channel levels (default)")
    p.add_argument("--demo", action="store_true", help="run a visible fade sequence")
    args = p.parse_args()

    if args.discover:
        discover()
        return

    if not args.host:
        p.error("a host (IP/hostname) is required unless --discover is used")
    if args.level is not None and not (0 <= args.level <= 100):
        p.error("--level must be 0..100")

    try:
        asyncio.run(run(args))
    except KeyboardInterrupt:
        sys.exit(130)


if __name__ == "__main__":
    main()
