# Mother PoE driver + Apple Home

Home Assistant can expose the Mother PoE driver's lights to **Apple Home** using
its built-in **HomeKit Bridge** — fully local (no cloud, no subscription), with
Siri control. There is no extra software and no change to the integration; you
enable one Home Assistant integration and pair it.

## Prerequisites

- Home Assistant on the **same LAN** as your iPhone/iPad and the driver, with the
  driver already added and its lights working.
- If Home Assistant runs in **Docker**, the container needs **host networking** —
  HomeKit is discovered over mDNS/Bonjour, which does not cross NAT. On Home
  Assistant OS / a Raspberry Pi this works out of the box.

## Steps

1. *Settings → Devices & Services → Add integration → **HomeKit Bridge***.
2. Choose what to expose — include the **Light** domain, or pick just the
   driver's `Channel 0` / `Channel 1` entities.
3. Submit. Home Assistant creates a bridge and shows a **pairing code** (also in
   a notification and on the integration's page).
4. On your iPhone: **Home app → + → Add Accessory → More options…** → select the
   Home Assistant bridge → enter or scan the pairing code.
5. The channels appear as **dimmable lightbulbs** in Apple Home — on/off,
   brightness, scenes, automations, and "Hey Siri, set the kitchen to 30%".

## Notes

- **Local only:** HomeKit runs over your LAN; nothing goes through the cloud, and
  no subscription is required.
- **Naming & rooms:** rename the lights and assign rooms in the Home app for a
  clean experience.
- **Not appearing in the Home app?** The iPhone can't reach Home Assistant over
  mDNS — usually because HA is behind NAT (Docker without host networking, or a
  separate VLAN/Wi-Fi). Put HA on the same LAN, or enable host networking.
- **One bridge is enough:** a single HomeKit bridge can expose many entities; you
  do not need one per driver.
