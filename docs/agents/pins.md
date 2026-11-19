# Firmware Families

Read for: Firmware family/platform facts and shared pin schemas.

These instructions supplement [AGENTS.md](../../AGENTS.md). Paths and YAML examples are
relative to the repository root unless stated otherwise.

## Firmware Families

The project currently distinguishes at least:

```yaml
firmware_family: esphome
firmware_family: libretiny
```

This value is defined by the board/base-board layer. Modules included through normal device configs
may assume it exists.

The same layer provides `firmware_platform`: `esp32`, `esp8266`, `bk72xx`, `rtl87xx`, or `ln882x`.
Use this platform fact for platform-specific schemas; `firmware_family: esphome` covers both ESP32
and ESP8266 and must not be used as a test for ESP32-only capabilities.

Important compatibility rule:

- ESP32 pin schemas accept `drive_strength`, `ignore_strapping_warning`, and
  `ignore_pin_validation_error`.
- ESP8266 and LibreTiny pin schemas reject those ESP32-only keys.

## Shared Pin Infrastructure

Use `packages/modules/pin.yaml` for reusable module pins unless there is a proven reason not to.
It supports:

- full GPIO pin schemas for switches, binary sensors, UART pins, outputs, and similar components
- `schema: number` for components such as Ethernet that accept pin-number schemas rather than full GPIO mappings
- a namespaced `pin:` vars object
- ESP32-specific pin keys only when `firmware_platform == 'esp32'`
- GPIO mappings without ESP32-only keys on ESP8266 and LibreTiny
- rejection of unsupported `pin.schema` values rather than silently selecting a GPIO schema

Preferred shape:

```yaml
pin: !include
  file: ../pin.yaml
  vars:
    pin:
      number: GPIO4
      inverted: false
      mode:
        output: true
      ignore_strapping_warning: false
```

`packages/modules/pin.yaml` is the sole implementation; the unused `pin/esphome.yaml` and
`pin/libretiny.yaml` alternatives have been removed. Its folded scalar evaluates to a mapping at
the pin include site, where package-level `defaults` are not valid. Keep this expression contained
and test its resolved output; do not copy it into unrelated modules. The normal board include
supplies `firmware_platform`; standalone users of the wrapper must supply that fact themselves.
The wrapper retains its existing defaults (GPIO0, false flags, and 20mA drive strength on ESP32).
`schema: number` emits only `number` and, on ESP32, `ignore_strapping_warning`; ESPHome's consuming
component remains responsible for validating the pin's supported modes and physical restrictions.
