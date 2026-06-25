# Mother PoE driver — Home Assistant integration

Control the **Mother PoE driver** from Home Assistant: drivers are discovered on
the local network, added with a click, and exposed as dimmable lights. Your Home
Assistant server also bridges the driver to **Loxone** and **KNX**, so one
integration serves every system. All the instructions are in this README and in
the [knowledge base page](https://motherdeveloper.github.io/mother-ha-driver/).

## Features

- **Auto-discovery** on the LAN (DHCP + mDNS) — often zero-touch.
- **Two dimmable lights** per driver, with smooth fades (`transition`).
- **Local & private** — talks directly to the driver over the LAN, no cloud.
- **Loxone bridge** — plain-text HTTP endpoints for the Miniserver.
- **KNX bridge** — drive the lights from KNX push-buttons via Home Assistant.
- **Apple Home & Siri** — expose the lights via Home Assistant's HomeKit Bridge.

> The Mother spots shift colour automatically with the level — warm when dimmed,
> ~4000 K daylight at full — so there is only a brightness control, by design.

## Install

### Via HACS (recommended)

1. In Home Assistant, install Home Assistant Community Store. Find the link to
   HACS install [here](https://www.hacs.xyz/docs/use/download/download/).
2. In HACS → ⋮ → **Custom repositories**, add this repository's URL, category
   **Integration**.
3. Search for **Mother PoE driver**, download it, and restart Home Assistant.

### Manual

Copy `custom_components/mother_mls25/` into your Home Assistant
`config/custom_components/` folder and restart.

## Add a driver

- **Automatic:** drivers appear under *Settings → Devices & Services →
  Discovered* → click **Add**. (Discovery needs Home Assistant to share the
  device's LAN; it will not fire when HA runs behind NAT, e.g. Docker Desktop on
  WSL2 — use manual entry there.)
- **Manual:** *Settings → Devices & Services → Add integration → Mother PoE
  driver* → enter the driver's IP address.

Each driver becomes a device with two lights, **Channel 0** and **Channel 1**.

## Other ecosystems

The Home-Assistant box doubles as a universal local hub:

- **Apple Home** — Home Assistant's built-in HomeKit Bridge exposes the lights
  to Apple Home and Siri, fully local. See [docs/apple-home.md](docs/apple-home.md).
- **Loxone** — the integration exposes plain-text HTTP endpoints
  (`/api/mls25/…`) that the Miniserver drives via Virtual Outputs/Inputs.
  See [docs/loxone.md](docs/loxone.md).
- **KNX** — Home Assistant's built-in KNX integration links the lights to KNX
  group addresses, no extra code. See [docs/knx.md](docs/knx.md).

A full quick-start for installers and users is in the
[knowledge base](https://motherdeveloper.github.io/mother-ha-driver/).

## How it works

The driver speaks **CoAP over UDP** (CBOR payloads) on the local network. The
integration translates Home Assistant commands to CoAP, polls the driver for
state (the firmware has no push), and re-exposes the lights over HTTP for other
controllers. Brightness is 0–100 % per channel; Home Assistant's `transition`
maps to the driver's fade rate.

## Repository layout

| Path | Purpose |
|---|---|
| `custom_components/mother_mls25/` | The Home Assistant integration. |
| `docs/` | Installer guides for Loxone and KNX. |
| `MotherPoEDriver-KnowledgeBase.html` | Single-page knowledge base for installers/users. |
| `poc/` | Standalone CoAP test script (development/diagnostics). |
| `webui/` | Optional standalone local control panel / HTTP bridge. |
| `hacs.json` | HACS metadata. |

## Development tools

A standalone CoAP test client lives in `poc/`:

```bash
cd poc
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

python test_coap.py --discover        # find drivers via mDNS
python test_coap.py <ip> --status     # read both channels
python test_coap.py <ip> --demo       # visible fade sequence
```

## License

Source-available under the [PolyForm Perimeter License 1.0.1](LICENSE): free to
use, modify and distribute, but **not** to build a product that competes with it
or to resell the software. This is not an OSI open-source license, so the
integration is distributed via a custom HACS repository (not the HACS default
store).
