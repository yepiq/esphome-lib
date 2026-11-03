# AGENTS.md - esphome-lib

## What This Repository Is

`esphome-lib` is a reusable ESPHome package library. It provides:

- board packages that describe MCU families and physical board targets
- base-board packages that add common ESPHome services and diagnostics
- appliance packages that assemble a board and its integrated peripherals
- networking packages for Wi-Fi, Ethernet, API, OTA, and mDNS
- functional modules for relays, lights, switches, energy monitors, and integrations
- concrete `devices/*.yaml` files that compose those packages into real devices
- minimal `kickstart/*.yaml` firmware for first UART flashes of supported boards

This repository is actively used. Treat it like production infrastructure: make small, deliberate,
validated changes, and preserve intentional device values.

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

### Appliance Packages

`packages/appliances/*.yaml` files represent complete, reusable hardware assemblies. An appliance
may select a concrete board package and compose integrated peripherals whose wiring is fixed by that
board. Use an appliance when it removes physical pin knowledge from device files and presents a
smaller capability-oriented API; do not use one merely to regroup a few component declarations.

`packages/appliances/radio-transceiver.yaml` is the shared radio hardware appliance. It supports:

- `heltec`: Heltec WiFi LoRa 32 V2 with its integrated SX127x radio and OLED
- `lilygo`: LilyGO TTGO LoRa32 V2.1 with its integrated SX127x radio and OLED
- `esp32dev_cc1101`: ESP32 DevKit with the library's standard external CC1101 wiring

Its public API separates the physical profile from the ESPHome driver:

```yaml
packages:
  - !include
    file: ../packages/appliances/radio-transceiver.yaml
    vars:
      radio:
        profile: lilygo # heltec | lilygo | esp32dev_cc1101
        driver: raw # sx127x | wmbus | raw
        frequency: 433.92MHz
        display:
          enabled: true
        raw:
          transmitter:
            enabled: true
          receiver:
            enabled: false
```

The `sx127x` and `wmbus` drivers are supported by both integrated-radio profiles. Raw TX and RX are
supported by `lilygo` and `esp32dev_cc1101`. Heltec routes SX127x DIO2 to input-only GPIO34, so its
`raw` driver supports RX only; enabling its raw transmitter intentionally fails validation.
`esp32dev_cc1101` is a raw-radio profile and has no integrated display. Unsupported profile/driver
combinations must fail configuration rather than silently selecting another hardware target.

The appliance owns the board target, SPI bus, transceiver wiring, optional raw transmitter/receiver,
integrated OLED wiring, font, and status LED. Applications own protocol settings, decoding,
automations, and user-facing entities. Stable infrastructure ids include `radio_spi`,
`radio_transceiver`, `radio_transmitter`, `radio_receiver`, `radio_i2c`, `radio_oled_font`,
`radio_display`, and `radio_status_led`. Raw-radio consumers may use the `radio_enter_tx`,
`radio_enter_rx`, `radio_enter_idle`, and `radio_after_transmit` scripts instead of knowing the
underlying radio component. Keep external component declarations and protocol-specific toolchain
workarounds in the consuming device when they are not intrinsic to the physical hardware.

`esp32_advanced` remains the standard top-level board var when including this appliance; do not nest
it under `radio`. The appliance must leave it unmodified so the selected original-ESP32 board can
distinguish an omitted object from explicitly provided framework settings.

`packages/appliances/heltec-hri-485x.yaml` is the HRI-485X family selector. Model profiles under
`packages/appliances/heltec-hri-485x/` own MCU, network, radio, and fixed GPIO facts. The family API
uses one `hri485x:` object; `hri485x.rs485` configures UART framing while the selected profile owns
the pins. The stable UART id is `hri485x_rs485_uart`. The appliance must not create a Modbus hub:
consuming products own `modbus`, controllers, polling, registers, and entities. Add profiles only
from a verified complete pin map, and never fall back to another HRI model for an unsupported profile.

`packages/appliances/waveshare-esp32-s3-eth-8di-8ro.yaml` owns the fixed W5500, TCA9554 relay bank,
isolated inputs, RS485 UART, RTC, RGB LED, buzzer, and MCU memory configuration of the matching
Waveshare board. Its public API is the `waveshare_8di8ro:` object. Per-channel configuration belongs
under `relays.relay1` through `relay8` and `digital_inputs.input1` through `input8`. Relay channels
always provide an appliance-owned physical output and use the shared relay-control framework for an
optional switch, light, or valve facade under `entity`; `entity.enabled: false` leaves only the
physical output. Digital-input channels may be removed with `enabled: false`. RS485, RTC,
relay-output, relay-entity, and input ids are configurable while retaining namespaced defaults. As
with the HRI appliance, consumers own Modbus hubs, protocol behavior, and input-to-relay automations.

`packages/appliances/waveshare-esp32-s3-touch-lcd-7b.yaml` owns the fixed 1024 x 600 RGB display,
GT911 touchscreen, backlight, memory configuration, and Waveshare-specific I2C extension of the
touch-enabled 7B board. Its public API is the `waveshare_lcd7b:` object. The extension at address
`0x24` is not compatible with the CH422G used by other Waveshare panels; use ESPHome's native
`waveshare_io_ch32v003` component. The display defaults are LVGL-ready, but applications own the
LVGL configuration or alternate display drawing behavior and any non-display onboard interfaces.
Stable default ids and the implemented wiring are documented under
`packages/appliances/waveshare-esp32-s3-touch-lcd-7b/README.md`.

`packages/appliances/kincony-kc868-a6.yaml` targets the original ESP32 KC868-A6, not the incompatible
ESP32-S3 A6v3. It owns the fixed relay/input expanders, analog I/O, RS485, RS232, SPI, I2C, OneWire
ports, and RTC. Its public API is the `kincony_kc868_a6:` object, with channel configuration under
`relays`, `digital_inputs`, `analog_inputs`, and `analog_outputs`. Relay channels always provide a
physical output and use the shared relay-control framework for an optional switch, light, or valve
facade under `entity`; `entity.enabled: false` leaves only the physical output. Existing short
infrastructure ids remain defaults, but relay-output, relay-entity, UART, RTC, and digital-input ids
are configurable. Consumers own serial protocols and automations.

Both relay appliances retain their established flat per-channel fields as compatibility defaults,
but new role configuration belongs under `entity`:

```yaml
relays:
  relay1:
    entity:
      type: light
      name: None
  relay2:
    entity:
      type: valve
      name: Irrigation Valve
      device_class: water
  relay3:
    entity:
      enabled: false
```

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

## Networking Framework

`packages/modules/networking.yaml` is included by `base-board.yaml`. Select one interface (or no
network) with `networking.mode`:

```yaml
vars:
  networking:
    mode: wifi # wifi | ethernet | none
```

Responsibilities:

- select interfaces through `networking.interfaces` (an ordered list of `wifi`/`ethernet`, or `[]`)
  or `networking.mode`; specifying both is invalid
- expose API, OTA, and mDNS defaults only with a network, with individual `enabled` controls
- own HA time, connectivity status and uptime's clock-dependent form; offline/no-clock uptime is
  elapsed seconds, with no fabricated clock or implicit network prerequisite
- use `pin.yaml` for Ethernet pin-number fields
- disable API and Wi-Fi connection-loss reboots by default with `reboot_timeout: 0s`

Ethernet type selects the physical schema. RMII PHYs use `mdc_pin`, `mdio_pin`, `clk_pin`,
`clk_mode`, and `phy_addr`; SPI controllers such as W5500 use `clk_pin`, `mosi_pin`, `miso_pin`,
`cs_pin`, `interrupt_pin`, and `reset_pin`. Keep those implementations separate because ESPHome
rejects fields from the wrong Ethernet schema.

Device-specific networking overrides should travel through the board package include so the base-board
layer and nested networking package see the same package context:

```yaml
packages:
  - !include
    file: ../packages/boards/espressif/m5stack-core-esp32.yaml
    vars:
      networking:
        mode: ethernet
        ethernet:
          type: IP101
          mdc_pin: GPIO23
          mdio_pin: GPIO18
          clk_pin: GPIO0
          power_pin: GPIO5
```

The two interface selectors use deferred includes. Keep them lazy: preloading all variants would
resolve Wi-Fi secrets even for Ethernet-only/offline devices. `networking/settings.yaml` is the
shared normalization used by the assembler and appliance-owned HA/RTC hooks; do not
duplicate those decisions in wrappers. Forward complete networking objects, retaining fixed
appliance Ethernet wiring. Clock synchronization and API LED hooks must not recreate disabled
services. Device-level HA actions and explicit clock references remain consumer prerequisites;
unsupported offline combinations must fail, not silently become no-ops.

Dual-interface mode uses ESPHome's native `network.priority`, requires ESP32/2026.8.0, and keeps
per-interface IP/MAC diagnostics distinct. Single-interface IDs, names and defaults are preserved.
Explicit Ethernet `enable_on_boot` also requires 2026.8.0; leave that schema key absent by default
so existing single-interface packages retain their minimum version.
Do not implement a custom failover loop. Test both priority orders, offline platforms, disabled
services, explicit RTC clocks and rejected dependencies. Consumer configuration and accepted
fields are documented in `packages/modules/networking/README.md`.

## Relay-Control Framework

`packages/modules/relay-control.yaml` is the public entrypoint for reusable relay-backed switch,
light, and valve behavior. It is an assembler package: it composes core relay behavior, one entity
type, one control target, and optional feature packages.

Relay-control concepts:

- POWER is the local physical relay output plus its logical state and command scripts.
- CONTROL is the logical target for external inputs and optional entity facades.
- CONTROL may map to POWER locally, call a detached Home Assistant entity, or remain no-op.
- ENTITY is the complete user-facing role configuration under `rc.entity`.
- PRIMARY is the command path that operates the selected ENTITY.

Supported `rc.entity.type` values:

- `switch` (default): use an output-backed switch as the POWER state owner and primary entity.
- `light`: for local control, use a binary light as the POWER state owner and drive the GPIO output
  directly. Detached lights and lights with separately exposed power use an output-backed POWER
  switch plus a CONTROL light facade.
- `valve`: retain an output-backed POWER switch as the state and restoration owner, then expose a
  binary CONTROL valve facade that reports that POWER state as open or closed.

Unsupported entity types and control modes must fail configuration. Do not add fallback branches
that silently turn misspelled enum values into another behavior.

Valve entities accept an optional `rc.entity.device_class` (`water`, `gas`, or empty). Do not assign
a generic valve device class when the physical medium is unknown.

Hardware profiles should describe fixed pins and physical features once, then forward the caller's
complete `entity` vars object as `rc.entity`. Do not unpack entity fields in each hardware profile.
Add future entity types such as fans to relay-control itself; hardware profiles must remain unchanged.

Single-relay device profiles expose this package API:

```yaml
files:
  - path: devices/tuya-mini-switch-1dc-5a.yaml
    vars:
      entity:
        type: valve
        name: Main Water Valve
        device_class: water
```

Omitting `entity` produces the default unnamed switch. Valve entities hide their backing power
switch by default. Local light entities do not create a backing switch unless it is needed;
`rc.entity.power.exposed: true` creates and exposes one separately, and `rc.entity.power.name` sets
its name. `rc.entity.icon` applies to the selected switch, light, or valve facade; a separately
exposed backing power switch uses `rc.entity.power.icon`. `rc.entity.enabled: false` suppresses the
facade, state owner, control scripts, and optional features while retaining the selected provider's
physical output. `rc.power.output_id` optionally overrides the physical output id, which otherwise
defaults to `${rc.id}_power_output`.

The default `rc.power.provider: gpio` creates that output from `rc.power.pin`. Appliance packages may
instead use `rc.power.provider: external`; the appliance must create the binary output itself and
pass its id through `rc.power.output_id`. This keeps fixed expander wiring in the appliance while
reusing the same entity and control behavior.

Core invariants:

- The local binary output is always present; a switch facade is created only when the selected role
  needs one.
- Exactly one component owns restored POWER state: an output switch, or a direct local binary light.
- `${rc.id}_power_state` is the stable internal binary sensor for observing POWER independently of
  its owner type. Device packages must not inspect `${rc.id}_power_relay` directly.
- `${rc.id}_power_on`, `${rc.id}_power_off`, and `${rc.id}_power_toggle` are the stable commands for
  operating POWER. Device packages must use these scripts instead of addressing the owner directly.
- Valve facades publish OPEN or CLOSED from the POWER state hooks so startup consumers never observe
  ESPHome's temporary default valve state.
- A POWER switch defaults to `None` when it is the primary switch entity. POWER remains independently
  controllable through its stable scripts even when CONTROL is detached.
- Indicator LEDs, when present, follow POWER state for safety.
- Integrated physical buttons, when present, toggle POWER.
- External wall-switch inputs toggle PRIMARY so facade state remains synchronized.
- Valve and adapter-style light entities target CONTROL while their POWER switch remains independent.
- The optional power-cycle feature exposes a template button backed by an `${rc.id}_power_cycle`
  script. The off-time defaults to `3s`; `rc.power_cycle.delay` overrides it when needed.

Relay-control exposes `${rc.id}_primary_on`, `${rc.id}_primary_off`, and
`${rc.id}_primary_toggle` scripts for physical inputs. Primary switch commands delegate directly to
CONTROL. Valve and adapter-style light commands operate their facade, which delegates the resulting
state to CONTROL; a direct local light owns POWER itself. Device-specific input components should
call these PRIMARY scripts rather than bypassing the selected facade.

`rc.entity.control.mode` values:

- `local`: CONTROL delegates to POWER.
- `detached`: CONTROL calls Home Assistant service/action on `rc.entity.control.entity_id`.
- `none`: CONTROL scripts remain no-op.

Low-level callers may define the same defaults under `rc.control`; values under `rc.entity.control`
take precedence.

Relay-control is multi-instance by design. Every generated id must include `rc.id` or another
caller-provided unique prefix. Do not move instance-specific values into global substitutions unless
there is no workable alternative.

Preferred include shape:

```yaml
packages:
  - !include
    file: ../packages/modules/relay-control.yaml
    vars:
      rc:
        id: r1
        entity:
          type: switch
          name: None
        power:
          pin: GPIO4
          inverted: false
          strapping: false
        control:
          mode: local
        power_cycle:
          enabled: true
          name: Power Cycle
```

## Package Design Standards

### ESPHome Version Requirements

`packages/boards/templates/base-board.yaml` is the sole writer of `esphome.min_version`. Each
device/module/feature contributes its own minimum through the additive global list:

```yaml
substitutions:
  esphome_requirements:
    - source: waveshare_io_ch32v003
      version: 2026.7.0
```

Use released `major.minor.patch` strings and a nonempty feature/source label. The base resolver
validates the entries and compares numeric version triples after package requirements have merged.
Lists concatenate, including repeated/nested includes; never replace the registry with a scalar
or a source-keyed mapping. Requirements are global facts, not module vars or defaults. Put an
optional feature's contribution inside its selected package so disabling it removes the requirement.
Packages with no additional requirement contribute nothing. Do not enumerate other modules' needs
or inspect networking in an appliance to calculate its version. The base contributes the library
floor independently of device-specific requirements.

Dashboard requirements use the same list. A native top-level `esphome.min_version` overrides the
resolver under ESPHome's merge rules and is outside this contract. CI scans YAML for other writers
and checks every passing config's resolved minimum against its complete requirement list. Keep the
resolver inline in the shared base template; no Python component or one-use include is needed.
See `packages/README.md` for the consumer contract and dashboard example.

### Defaults, Vars, And Substitutions

- Public reusable module APIs must use one namespaced object under `vars:` such as `rc:`, `pin:`,
  `networking:`, or `energy:`.
- Use `defaults:` to normalize namespaced objects into local helper values inside the module.
- Use guarded lookups such as `rc.get("power", {}).get("pin", "GPIO0")`; do not rely on deep
  default merging.
- Use global `substitutions:` for device-local aliases, names, friendly names, board facts, and
  ESPHome values that are intentionally global.
- Avoid global substitutions for reusable module inputs.
- Internal package references may use private-looking names such as `_rc_target_local_pkg`.
- Keep defaults close to the module that owns them.

### IDs And Names

- Generated ids in reusable modules must be deterministic and collision-safe.
- Multi-instance modules must include an instance prefix such as normalized `rc_id` in every
  generated id.
- Internal id prefixes must not leak into user-facing entity names. Give entities neutral defaults
  and expose an explicit module name option when callers may need another label.
- Shared base-board diagnostics may use stable `mcu_*` ids.
- Single-instance modules may use simple ids only when the module is clearly not multi-instance.
- When a device has one obvious primary entity, prefer `name: None` so Home Assistant presents it
  using the device name. Ask before selecting a primary entity when the choice is ambiguous.
- Do not change entity names just because they look odd. Some names intentionally influence Home
  Assistant display behavior.

### Optional Features

- Optional subcomponents should be opt-in and easy to disable.
- Prefer clear namespaced booleans such as `rc.indicator_led.enabled`,
  `rc.external_switch.enabled`, or `rc.power_cycle.enabled`.
- Disabled optional packages should contribute no components.
- Feature flags should not require callers to pass irrelevant pins or entity ids.

### Includes And Conditional Packages

- Prefer list-form `packages:` entries:

```yaml
packages:
  - !include ../packages/modules/example.yaml
```

- Use real `!include` blocks with `vars:` when passing module variables.
- Be careful with named package entries; use them only when they are clearly needed.
- Do not return raw `{file: ..., vars: ...}` package dictionaries from expressions.
- Validate conditional include behavior with `esphome config` before applying it broadly.

The library floor is ESPHome 2026.10.0. Use native `!include` blocks with `condition:` for
optional file-backed packages, preserving their existing vars and ids. Keep unique inline
device behavior inline; conditional includes do not justify extracting one-use files.

## YAML Coding Standards

- Avoid quotes unless YAML requires them.
  - Empty string values may use `''`.
  - Plain values such as `local`, `detached`, `rocker`, `light.turn_on`, and `RESTORE_DEFAULT_OFF` should remain unquoted.
- Preserve existing quoted values when they appear intentional.
- Prefer readable YAML over compact one-liners.
- Keep comments short and useful.
- Do not add explanatory comments for obvious YAML.
- Let `device_class` select the default Home Assistant icon. Set `icon` only for an intentional
  override or when the entity has no suitable device class.

ESPHome component attribute order:

```text
platform
name
id
visibility/internal/entity category
pin/output/entity-specific options
automations/actions
```

When both `name` and `id` are present, prefer `name` before `id`.

## ESPHome Templating Standards

ESPHome templating behavior depends on version and context. Be conservative.

Known fragile patterns:

- returning schema-sensitive mappings from `${ ... }`
- using dynamic paths inside nested `!include` wrappers
- using YAML merge (`<<`) with `${ ... }` values
- returning raw package dictionaries with `file` / `vars` from expressions
- relying on named package entries where list-form entries are clearer

If a templating approach is required for reusable infrastructure, validate it with `esphome config`
on concrete ESPHome and LibreTiny devices when applicable.

The RF fan device keeps its per-address entity generation and captured C++ blocks inline. Prefer
readable template blocks to assembling C++ one quoted line at a time. For template-only rewrites,
compare resolved configuration and lambda text to confirm that emitted C++ is unchanged; the RF
consumer matrix in `tests/cases.yaml` covers both radios and the supported fan composition options.

## Dependency Workarounds

When a defect is traced to ESPHome, LibreTiny, PlatformIO, an SDK, or another dependency, do not
stop at identifying the upstream fault. Proactively evaluate workaround layers in this order:

1. Existing configuration or extension hooks
2. Application-level overrides
3. Linker wrapping, symbol aliases, and build flags
4. Small external components
5. Temporary dependency patches or forks

Prefer the narrowest reversible solution that keeps upstream dependencies unmodified. Verify the
mechanism against the relevant source and actual toolchain before recommending or implementing it.
Document the upstream issue, any version-specific assumptions, and how to remove the workaround
after an official fix becomes available.

### Pending: Remove The Beken UART Read Guard

Monitor [LibreTiny issue #154](https://github.com/libretiny-eu/libretiny/issues/154) and
[PR #432](https://github.com/libretiny-eu/libretiny/pull/432). The shared Beken template loads
`bk72xx_uart_guard` to protect `SerialClass::read()` with saved/restored IRQ and FIQ masks.
It is required by the interrupt-unsafe receive ring in LibreTiny 1.13.0. Do not copy the ARMv5
mask implementation into the Realtek or Lightning templates.

Once ESPHome's selected LibreTiny release includes the upstream fix, verify the actual Serial
read and interrupt handling in that release, then remove the local read wrapper and linker flag
from the shared Beken layer. Validate and compile BK7231N and BK7238 consumers and check that
serial reads remain interrupt-safe.

### Pending: Remove The Beken OTA Packaging Workaround

The shared Beken template loads `bk72xx_ota_packaging` to select PyCryptodome in LibreTiny's
build environment. ltchiptool 4.15.0's PyAES backend adds a second AES padding layer, which
can trigger a BK7231N bootloader verification defect at a 4096-byte compressed-input boundary.
Track the [upstream AES wrapper](https://github.com/libretiny-eu/ltchiptool/blob/master/ltchiptool/util/crypto.py).
Once the supported release fixes backend padding consistency, verify an ARM-host Beken build
and remove the component and base-board declaration. See the component README for history.

### Pending: Remove The Realtek Reboot Workaround

During ESPHome upgrades, check the LibreTiny version actually selected for RTL8720C builds.
[LibreTiny PR #397](https://github.com/libretiny-eu/libretiny/pull/397), released in 1.14.0,
changes `lt_reboot()` to call `sys_reset()`.

Once the library's supported ESPHome baseline selects LibreTiny 1.14.0 or later with that fix,
remove `-Wl,--wrap=lt_reboot` and `-Wl,--defsym=__wrap_lt_reboot=sys_reset` from
`packages/boards/templates/base-board-libretiny-realtek.yaml`. Run configuration validation and
compile an affected WBR3/RTL8720C target, such as `devices/fan-scheeair-nova-100.yaml`, confirming
the resolved framework version and absence of both flags. Remove this pending note when complete.

## Validation Standards

- Consumer README changes: run `python tests/docs_config.py` for complete examples and
  `python -m unittest discover -s tests -p 'test_*.py'` for local links/catalog coverage.
  The README runner mirrors this repository to checked-out packages and uses local components.
  Partial snippets still need their documented context; never treat an HA script as ESPHome YAML.

- YAML configuration-only changes: run `esphome config` only. Do not compile firmware for
  substitutions, metadata, package selection, or other configuration-only changes.
- C++ changes, including lambda bodies embedded in YAML: run config first, then compile only
  affected targets. Use focused host tests for behavioral logic. Do not compile the whole fleet.
- Devices must inherit logger thresholds from the base template. Keep hardware requirements such
  as `baud_rate: 0`; leave global/per-tag verbosity to the consuming ESPHome dashboard.
- Do not increment project versions for unpublished edits.

For local development, select checked-out components before ESPHome processes external sources:

```bash
cd devices
ESPHOME_LIB_SOURCE="$(pwd)/../components" esphome config sonoff-basic-r4.yaml
```

All declarations for this repository's components must include `packages/component-source.yaml`.
Without the environment variable, it selects the unpinned GitHub repository. Do not add self-repo
version pins or append a local source after a remote source (that still fetches the remote first).

The isolated regression suite uses dummy secrets and local components; run it with a Python
interpreter that has ESPHome installed. It performs no firmware compilation:

```bash
python tests/validate.py
python tests/validate.py --all
```

See `tests/README.md` for focused targets, host tests, known failures and CI behavior.

Choose validation targets by impact:

- Base-board, networking, or common diagnostics: validate at least one Wi-Fi ESPHome device and one relevant Ethernet or LibreTiny device.
- Pin wrapper changes: validate an ESPHome device and a LibreTiny device.
- Relay-control changes: validate a relay-control device and any device mode touched by the change.
- Device-only changes: validate that device.

When validation fails, report the first real error block and the file involved.

## Editing Discipline

- Inspect before editing.
- Change only files relevant to the task.
- Preserve unrelated user changes.
- Do not clean up generated ESPHome cache/build output unless explicitly asked.
- Do not rename, move, or reorganize packages unless explicitly asked.

## Reporting Back

Commit messages should describe the resulting change and relevant validation. Omit conversation
history, commit-splitting mechanics, and references to unpublished work in other commits.

When reporting changes:

- summarize what changed
- mention files changed
- include validation results or the first remaining error
- call out any ESPHome-version-specific workaround
