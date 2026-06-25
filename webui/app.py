#!/usr/bin/env python3
"""
Tiny local control panel for the Mother MLS25 PoE+ LED driver.

A browser cannot speak CoAP/UDP directly, so this little web server acts as a
bridge: it serves an HTML control panel and translates its button/slider clicks
into CoAP requests to the driver.

Run it, then open http://localhost:8080 in your browser.

  python app.py            # auto-discover the driver via mDNS
  python app.py 192.168.1.158   # or point it at a known IP
"""

import argparse
import asyncio
from pathlib import Path

import cbor2
from aiocoap import Code, Context, Message
from aiohttp import web

COAP_PORT = 5683
CONTENT_FORMAT_CBOR = 60
NUM_CHANNELS = 2
COAP_TIMEOUT = 8
HERE = Path(__file__).parent

coap_ctx: Context | None = None
DEVICE_HOST: str = ""


# --------------------------------------------------------------------------- #
# CoAP bridge
# --------------------------------------------------------------------------- #

async def coap_get_level(ch: int) -> int:
    msg = Message(code=Code.GET, uri=f"coap://{DEVICE_HOST}:{COAP_PORT}/led/{ch}")
    resp = await asyncio.wait_for(coap_ctx.request(msg).response, COAP_TIMEOUT)
    data = cbor2.loads(resp.payload) if resp.payload else {}
    return data.get("lvl")


async def coap_set_level(ch: int, lvl: int, rate=None) -> None:
    payload = {"lvl": int(lvl)}
    if rate is not None:
        payload["rate"] = int(rate)
    msg = Message(code=Code.POST, uri=f"coap://{DEVICE_HOST}:{COAP_PORT}/led/{ch}",
                  payload=cbor2.dumps(payload))
    msg.opt.content_format = CONTENT_FORMAT_CBOR
    await asyncio.wait_for(coap_ctx.request(msg).response, COAP_TIMEOUT)


async def coap_onoff(ch: int, on: bool) -> None:
    path = "on" if on else "off"
    msg = Message(code=Code.POST, uri=f"coap://{DEVICE_HOST}:{COAP_PORT}/led/{ch}/{path}")
    await asyncio.wait_for(coap_ctx.request(msg).response, COAP_TIMEOUT)


# --------------------------------------------------------------------------- #
# HTTP handlers
# --------------------------------------------------------------------------- #

@web.middleware
async def cors_mw(request: web.Request, handler):
    """Allow the panel to call the API even when opened from another origin."""
    if request.method == "OPTIONS":
        resp = web.Response()
    else:
        resp = await handler(request)
    resp.headers["Access-Control-Allow-Origin"] = "*"
    resp.headers["Access-Control-Allow-Methods"] = "GET, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Content-Type"
    return resp


async def h_index(request: web.Request) -> web.Response:
    return web.FileResponse(HERE / "index.html")


async def h_status(request: web.Request) -> web.Response:
    channels = []
    for ch in range(NUM_CHANNELS):
        try:
            channels.append({"ch": ch, "level": await coap_get_level(ch)})
        except Exception as exc:  # noqa: BLE001
            return web.json_response({"error": f"{type(exc).__name__}: {exc}"}, status=502)
    return web.json_response({"host": DEVICE_HOST, "channels": channels})


async def h_set(request: web.Request) -> web.Response:
    body = await request.json()
    try:
        await coap_set_level(int(body["ch"]), int(body["level"]), body.get("rate"))
    except Exception as exc:  # noqa: BLE001
        return web.json_response({"error": str(exc)}, status=502)
    return web.json_response({"ok": True})


async def h_onoff(request: web.Request) -> web.Response:
    body = await request.json()
    try:
        await coap_onoff(int(body["ch"]), bool(body["on"]))
    except Exception as exc:  # noqa: BLE001
        return web.json_response({"error": str(exc)}, status=502)
    return web.json_response({"ok": True})


# --------------------------------------------------------------------------- #
# Lifecycle + discovery
# --------------------------------------------------------------------------- #

async def on_startup(app: web.Application) -> None:
    global coap_ctx
    coap_ctx = await Context.create_client_context()


async def on_cleanup(app: web.Application) -> None:
    if coap_ctx is not None:
        await coap_ctx.shutdown()


def discover(timeout: float = 4.0):
    """Return the first MLS25 IP found via mDNS, or None."""
    try:
        from zeroconf import ServiceBrowser, ServiceListener, Zeroconf
    except ImportError:
        return None
    import time

    found = []

    class Listener(ServiceListener):
        def add_service(self, zc, type_, name):
            info = zc.get_service_info(type_, name)
            if info:
                found.extend(info.parsed_scoped_addresses())

        def update_service(self, zc, type_, name):
            self.add_service(zc, type_, name)

        def remove_service(self, zc, type_, name):
            pass

    zc = Zeroconf()
    ServiceBrowser(zc, "_mother-life._udp.local.", Listener())
    try:
        time.sleep(timeout)
    finally:
        zc.close()
    return found[0] if found else None


def main() -> None:
    global DEVICE_HOST
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("host", nargs="?", help="driver IP/hostname (default: auto-discover)")
    ap.add_argument("--web-port", type=int, default=8080)
    args = ap.parse_args()

    DEVICE_HOST = args.host or ""
    if not DEVICE_HOST:
        print("Discovering the driver via mDNS ...")
        DEVICE_HOST = discover() or ""
    if not DEVICE_HOST:
        raise SystemExit("No driver found. Pass its IP, e.g.  python app.py 192.168.1.158")

    print(f"Driver: {DEVICE_HOST}")
    print(f"Open your browser at: http://localhost:{args.web_port}")

    app = web.Application(middlewares=[cors_mw])
    app.add_routes([
        web.get("/", h_index),
        web.get("/api/status", h_status),
        web.post("/api/set", h_set),
        web.post("/api/onoff", h_onoff),
    ])
    app.on_startup.append(on_startup)
    app.on_cleanup.append(on_cleanup)
    web.run_app(app, host="127.0.0.1", port=args.web_port, print=None)


if __name__ == "__main__":
    main()
