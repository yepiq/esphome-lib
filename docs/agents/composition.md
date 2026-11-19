# Composition Model

Read for: Device, kickstart, board and base-board changes.

These instructions supplement [AGENTS.md](../../AGENTS.md). Paths and YAML examples are
relative to the repository root unless stated otherwise.

## Composition Model

The library is layered. Most concrete devices follow this shape:

```text
devices/<device>.yaml
  -> packages/appliances/<appliance>.yaml (when a complete hardware assembly exists)
    -> packages/boards/<vendor-or-family>/<board>.yaml
    -> packages/modules/*.yaml
  -> packages/boards/<vendor-or-family>/<board>.yaml (otherwise)
    -> packages/boards/templates/base-board-<family>.yaml
      -> packages/boards/templates/base-board.yaml
        -> packages/modules/networking.yaml
  -> optional packages/modules/*.yaml
  -> device-specific components and overrides
```

### Devices

`devices/*.yaml` files are concrete firmware configurations. They should mostly:

- define device substitutions such as `name`, `friendly_name`, pins, inversion flags, and feature choices
- include exactly one board package, directly or through an appliance package
- include reusable modules when possible
- contain device-specific behavior only when it truly belongs to that one device
- omit `esphome.project` and `dashboard_import` from reusable hardware profiles; complete product
  definitions may provide that metadata

Do not casually change names, pins, restore modes, or entity names in device files.
Values like `none`, `None`, quoted booleans, commented pin options, or unusual defaults may be
intentional for a specific device or for Home Assistant entity behavior.

Keep each device's unique configuration and behavior in its single `devices/<device>.yaml` file.
Do not create device subdirectories for one-use helpers or notes; keep concise device-specific
notes in the YAML. Extract includes for actual reuse, not merely to shorten a device file.
Prefer validated inline conditional blocks for device-only optional behavior. A separate file
without reuse needs a concrete technical benefit, such as lazy loading of an optional secret
that ESPHome would otherwise require even when the feature is disabled; explain the exception
before adding it.

Hardware-only variants with the same device behavior belong in one device definition with an
explicit profile selector. `tuya-ct-clamp-2em-80a.yaml` uses `ct_clamp.profile` (`cb2s` or `t1m`),
with T1-M-only alarms kept in an inline conditional package. `tuya-strip-4pm.yaml` uses
`power_strip.profile` (`cbu` or `t1u`) with inline wiring data. Preserve the established substitutions,
entity IDs and metadata when consolidating variants. Unsupported profiles must fail validation.
Test both standalone device defaults and dashboard includes; root-device package selection needs
substitution helpers, whereas include-only modules can normalize their vars using `defaults`.
MELcutter versions and Feyree chargers remain separate products, not hardware profiles.
Consumer parameters and dashboard examples are in `devices/README.md`.

### Kickstart Firmware

`kickstart/*.yaml` files are temporary board bring-up configurations. Each kickstart should:

- map one-to-one to a concrete package under `packages/boards/`
- include that board package and no application-specific components
- use a generic kickstart identity

Name firmware files `kickstart-<board-package>.yaml`. Add aliases only when an established
flashing workflow needs them.

### Board Packages

`packages/boards/*/*.yaml` files describe hardware targets. They should:

- include the appropriate base-board template
- define the ESPHome platform component (`esp32`, `esp8266`, `bk72xx`, `rtl87xx`, etc.)
- set board, variant, framework, and family-specific compatibility options
- avoid device behavior such as relay logic, sensors, lights, and user-facing automations

Board packages may define platform facts such as `firmware_family` through the base-board pipeline.

### Base-Board Packages

`packages/boards/templates/base-board*.yaml` files provide shared firmware foundations:

- `esphome` name/friendly name and minimum ESPHome version
- logger defaults
- API, OTA, mDNS, and networking through `packages/modules/networking.yaml`
- common diagnostics such as uptime, status, version, restart button, and time
- family-specific adjustments for ESPHome, LibreTiny, ESP8266, ESP32, Beken, and Realtek

Keep base-board packages broad and boring. If a behavior is not useful across many devices, it
probably belongs in a device file or a functional module instead.

The shared ESP32-family template accepts `esp32_advanced.flash_chip` through the board include's
vars. It forwards this option only when explicitly supplied, with no library default. Use the
vendor recommended by the device's boot log; never assume one flash vendor across all boards.
This setting applies across ESP32 variants, independently of the original-ESP32-only options below.

Original ESP32 boards include `base-board-esphome-esp32-classic.yaml` between their concrete board
package and the shared ESP32-family template. It exposes original-ESP32-only build settings through
an optional `esp32_advanced:` vars object:

```yaml
vars:
  esp32_advanced:
    minimum_chip_revision: 3.1
    sram1_as_iram: true
```

The shared classic-ESP32 template provides no defaults for either option. When `esp32_advanced` is
absent, it contributes no `framework.advanced` configuration. When one key is present, only that key
is forwarded; explicit values such as `sram1_as_iram: false` are preserved. Concrete hardware
profiles may set an option after running hardware reports the required chip revision or bootloader
support. Do not pass these options to C3, C6, S2, S3, or other ESP32 variants.
