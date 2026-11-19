# Functional Modules

Read for: Functional modules, shared device behavior and wMBus profiles.

These instructions supplement [AGENTS.md](../../AGENTS.md). Paths and YAML examples are
relative to the repository root unless stated otherwise.

### Functional Modules

`packages/modules/*.yaml` files add reusable behavior. Modules should be designed around explicit
inputs and narrow responsibilities.

Important modules:

- `networking.yaml` selects Wi-Fi, Ethernet, or no network support and owns API/OTA/mDNS defaults.
- `pin.yaml` is the shared pin schema wrapper used by modules that need ESPHome/LibreTiny-safe pins.
- `relay-control.yaml` is the public relay-control assembler and composes smaller relay-control packages.
- `appliance-relay.yaml` connects an appliance-owned binary output to the shared relay-control API.
- `output-switch.yaml` is the low-level output-backed switch used by relay-control where state
  ownership requires it.
- `energy-monitoring-bl0937.yaml` and `energy-monitoring-bl0942.yaml` expose reusable energy monitor setups.
- `homekit.yaml` adds HAP-ESPHome support and ESP32 framework options.
- `radio/driver.yaml` and `radio/display.yaml` provide the capability layers used by the radio appliance.
- `wmbus/qwater-meter.yaml` exposes one complete QWater meter entity profile per include.
- `relay-group.yaml` aggregates existing relay-control POWER states and commands. Physical wiring,
  member grouping, and the indicator light remain device-owned.
- `fan-power-sync.yaml` shares a template fan's power-switch command flow. MCU feedback, speed
  mappings, guards and oscillation commands remain explicit in each consuming device.
- `tuya-ct16-channel.yaml` is the CT16 product's repeated channel entity profile. Do not move its
  raw decoder or infer a common protocol for unrelated meters from this profile.

These helpers have consumer contracts in `packages/modules/README.md`. Keep all existing explicit
IDs, names, categories and restoration behavior when adopting them. The fan helper does not make
Pro Breeze and JUMMICO interchangeable protocols; test their different feedback policies separately.

Prefer a module over copy/paste device logic when the behavior is reusable. Prefer device-local YAML
when the behavior is unique, experimental, or depends on one physical product.

### wMBus Meter Profiles

`packages/modules/wmbus/qwater-meter.yaml` is a multi-instance profile for QWater meters. It creates
the meter component plus its RSSI, current volume in cubic metres, derived consumption in litres,
end-of-month, end-of-year, and corresponding date entities. The receiver must already provide a
`wmbus_radio`; the radio appliance exposes it as `radio_transceiver`.

```yaml
packages:
  - !include
    file: ../packages/modules/wmbus/qwater-meter.yaml
    vars:
      meter:
        id: main_water
        name: Water Main
        meter_id: 0x12345678
```

`meter.id` prefixes every generated id and must be unique. `meter.radio_id` defaults to
`radio_transceiver`. Including the profile multiple times automatically registers the QWater driver,
so a separate `wmbus_common.drivers` entry is unnecessary unless additional uninstantiated drivers
are required. QWater date fields are `PointInTime` values, which the current adapter does not expose
to `wmbus_meter` text sensors. The profile therefore publishes its date template sensors from the
meter's `on_telegram` callback and marks them with the native `date` device class. Last Update uses
the adapter's UTC timestamp field and native `timestamp` device class; the meter clock remains text
because its reported wall-clock value has no timezone.
