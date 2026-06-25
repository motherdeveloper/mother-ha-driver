# MLS25 + Loxone

Loxone is a closed system: you cannot run code on the Miniserver, and it does
not speak the driver's CoAP/CBOR protocol. So **Home Assistant on a small box
(e.g. a Raspberry Pi) acts as the bridge**: the MLS25 integration adds plain-text
HTTP endpoints that the Loxone Miniserver calls with its built-in **Virtual
Outputs** (control) and **Virtual Inputs** (status). HA translates HTTP → CoAP.

```
Loxone Miniserver ──HTTP──► Home Assistant (this integration) ──CoAP/CBOR──► MLS25
```

## Prerequisites

- Home Assistant running on the **same LAN** as the Miniserver and the drivers,
  with this integration installed and each driver added.
- Give each driver a **fixed IP** (DHCP reservation in your router). The Loxone
  config references the driver, so its IP should not change.
- Know your HA box IP and port. **`192.168.1.50` below is only an example** —
  use *your* HA machine's real LAN IP (on Windows: `ipconfig` → IPv4 Address).
  The Miniserver is a separate device, so never use `localhost`.

## The endpoints (provided by the integration)

| Purpose | URL (GET) | Returns |
|---|---|---|
| Read level | `/api/mls25/level?ch=0` | `60` |
| Set level (0–100) | `/api/mls25/set?ch=0&level=<v>` | `OK` |
| Set level + fade | `/api/mls25/set?ch=0&level=<v>&rate=20` | `OK` |
| Turn on | `/api/mls25/on?ch=0` | `OK` |
| Turn off | `/api/mls25/off?ch=0` | `OK` |

`ch` is `0` or `1`. Add `&host=192.168.1.158` to target a specific driver when
you have more than one (otherwise the first configured driver is used).

> No token or JSON — plain text on purpose, so Loxone parses it directly. The
> endpoint is unauthenticated; keep it on a trusted LAN.

### Quick test before touching Loxone

From any PC on the LAN:

```
curl "http://192.168.1.50:8123/api/mls25/level?ch=0"     # -> 60
curl "http://192.168.1.50:8123/api/mls25/set?ch=0&level=30"
```

## Loxone Config setup

> Field names vary slightly between Loxone Config versions; map the values below
> to the matching fields.

### 1. Virtual Output (the connection)
- **Create** a *Virtual Output*.
- **Address:** `http://192.168.1.50:8123`  (your HA box)

### 2. Dimming a channel — Virtual Output Command (analog)
- Add a *Virtual Output Command* under that Virtual Output.
- **Command for ON:** `/api/mls25/set?ch=0&level=<v.0>`
  (the `.0` sends a whole number; the endpoint also accepts decimals since v0.3.1)
- Leave it **analog** (uncheck "use as digital output").
- **Scaling** — make the value pass through 1:1 (a 0–100 dim value becomes
  `level=0..100`):
  - **Input value 1** (*Ingang waarde 1*): `0`
  - **Input value 2** (*Ingang waarde 2*): `100`
  - **Unit** (*Eenheid*): `%` (display only, optional)
- `<v>` is replaced by Loxone with the scaled value. (For channel 1, use `ch=1`.)

> Field labels vary between Loxone Config versions. The key idea: the analog
> command holds the URL with `<v>`, and the two "input value" fields define the
> 0–100 range that flows into `<v>`.

On/off is covered by the dimmer (`level=0` = off). If you prefer explicit
digital commands, make a digital Virtual Output Command with
**ON** = `/api/mls25/on?ch=0` and **OFF** = `/api/mls25/off?ch=0`.

### 3. Create a control element (the dim knob)
The Virtual Output Command is only the *output* ("the socket"). You still need a
*control* and must wire them together on a programming page.

**Quickest — a slider in the Loxone app:**
1. **Virtual Inputs → Add Virtual Input** (the plain one, *not* the HTTP input).
2. In its properties: uncheck "use as digital input" (so it is **analog**), set
   **Min** `0`, **Max** `100`, step `1`, unit `%`.
3. On a **programming page**, drag in both the **Virtual Input** (has an output)
   and the **Virtual Output Command** (has an input), then draw a wire from the
   input's output to the command's input.
4. **Assign the Virtual Input to a Room *and* a Category** — without both it will
   not appear in the app.
5. **Save → upload to the Miniserver.** The slider shows in the app; dragging it
   dims the spot.

**For a real light tile (push-button behaviour):** use a **Dimmer** or
**Lighting Controller** block. Feed it from a push-button (Virtual Input as
button), and wire the block's analog output (AQ) to the Virtual Output Command.
This renders as an on/off + brightness tile in the app.

### 4. Reading status back — Virtual Input (HTTP)
- **Create** a *Virtual HTTP Input*.
- **Address / poll URL:** `http://192.168.1.50:8123/api/mls25/level?ch=0`
- **Polling interval:** e.g. `5` s.
- Add a *Virtual HTTP Input Command*:
  - **Command recognition:** `\v`  (the whole response is the number)
  - This gives you a 0–100 analog input you can show or feed into logic.

Repeat the dimming command and the HTTP input for `ch=1` to control the second
channel.

## Notes

- HA sits in the control path, so a button press goes Loxone → HA → driver
  (typically well under a second for lighting).
- The `rate` parameter (0–100, higher = faster) maps to the driver's fade speed;
  omit it to use the firmware default.
- For production, run HA on an always-on box (Pi/NUC/NAS-Docker), not a laptop.
