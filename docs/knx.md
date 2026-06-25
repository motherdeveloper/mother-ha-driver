# MLS25 + KNX

The MLS25 is not a KNX device, but **Home Assistant on a small box (e.g. a
Raspberry Pi) bridges it onto the KNX bus** using HA's built-in KNX integration
(`xknx`). No extra code is needed — the MLS25 lights are normal HA entities, and
HA's KNX integration links them to KNX group addresses.

```
KNX push-button ──KNX bus──► KNX/IP gateway ──IP──► Home Assistant ──CoAP/CBOR──► MLS25
```

## Prerequisites

- A **KNX/IP gateway** (router or interface) on the installation — standard for
  any IP-integrated KNX system.
- Home Assistant on the same LAN, with this integration installed and the
  driver(s) added (preferably on a fixed IP via DHCP reservation).
- The HA **KNX integration** configured against your gateway.
- Group addresses planned in ETS, e.g. for channel 0:
  - `1/1/0` — on/off command (DPT 1.001)
  - `1/1/1` — absolute dim command, 0–100 % (DPT 5.001)
  - `1/1/2` — on/off status (DPT 1.001)
  - `1/1/3` — brightness status, 0–100 % (DPT 5.001)

## Two directions

1. **KNX → MLS25 (control):** HA listens to the push-button's group addresses
   (`knx_event`) and an automation drives the light.
2. **MLS25 → KNX (status/feedback):** `knx.expose` puts the light's state back
   on the bus for visualisations and status LEDs.

## Example configuration

`configuration.yaml`:

```yaml
knx:
  # Connect to your gateway. If it is auto-discovered you can omit this;
  # otherwise pick one:
  # routing: {}                 # KNX/IP routing (multicast)
  # tunneling:
  #   host: 192.168.1.10
  #   port: 3671

  # Fire knx_event for the addresses the push-buttons send to:
  event:
    - address: "1/1/0"          # on/off command for channel 0
    - address: "1/1/1"          # dim command for channel 0 (0-100%)

  # Push the light's status back onto the bus:
  expose:
    - type: binary
      entity_id: light.mls25_192_168_1_158_channel_0
      address: "1/1/2"
    - type: percent
      entity_id: sensor.mls25_ch0_brightness_pct
      address: "1/1/3"

# Convert HA brightness (0-255) to 0-100% for the KNX status expose:
template:
  - sensor:
      - name: "MLS25 ch0 brightness pct"
        unique_id: mls25_ch0_brightness_pct
        unit_of_measurement: "%"
        state: >
          {% set b = state_attr('light.mls25_192_168_1_158_channel_0', 'brightness') %}
          {{ ((b | int(0)) / 255 * 100) | round(0) }}
```

`automations.yaml` (or build these in the UI):

```yaml
- alias: "KNX -> MLS25 ch0 on/off"
  trigger:
    - platform: event
      event_type: knx_event
      event_data:
        destination: "1/1/0"
  action:
    - if: "{{ trigger.event.data.data in [1, true] }}"
      then:
        - service: light.turn_on
          target: { entity_id: light.mls25_192_168_1_158_channel_0 }
      else:
        - service: light.turn_off
          target: { entity_id: light.mls25_192_168_1_158_channel_0 }

- alias: "KNX -> MLS25 ch0 dim"
  trigger:
    - platform: event
      event_type: knx_event
      event_data:
        destination: "1/1/1"
  action:
    - service: light.turn_on
      target: { entity_id: light.mls25_192_168_1_158_channel_0 }
      data:
        brightness_pct: "{{ trigger.event.data.data | int }}"
```

Duplicate the blocks with `channel_1` and another set of group addresses for the
second channel.

## Notes & gotchas

- Replace the entity IDs and group addresses with your own. Find the entity ID
  under **Settings → Devices & Services → Entities**.
- The exact `knx_event` payload field can differ by HA version. Verify it live:
  **Developer Tools → Events → listen to `knx_event`**, press the button, and
  check whether the value is under `data.data` or `data.value`. Adjust the
  templates accordingly.
- HA is in the control path (KNX button → HA → driver), fine for lighting but
  not bus-native instant.
- A customer who insists the device itself be a **certified KNX device** needs
  different hardware/firmware — that is a separate product, out of scope here.
