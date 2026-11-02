# Shared Behavior Modules

Start with the [device reference](../../devices/README.md) when firmware already exists for your
hardware. The following contracts are for composing an application from modules. A board package
must provide the shared firmware foundations. Native ESPHome component settings are not implicitly
accepted as package parameters: use the fields listed here, or a native `!extend` override.

## RF Receiver

[`remote-receiver-rc-switch.yaml`](remote-receiver-rc-switch.yaml) accepts a `receiver` object:
`enabled` (false), `id` (`rc_switch_receiver`), `pin` (`GPIO0`), `inverted` (false),
`buffer_size`, `filter` (`150us`) and `idle` (`4ms`). Disabled receivers contribute no components.
The buffer is measured in bytes: the default is `4kb` on supported ESP32 RMT targets and `16kb`
on ESP8266/LibreTiny. Multiply custom pre-2026.10 ESP8266/LibreTiny values by four to preserve
their previous pulse capacity. Explicit buffer values are forwarded without scaling.

## Relay Control

[`relay-control.yaml`](relay-control.yaml) accepts one `rc` object. It creates a physical binary
output, a state owner and an optional user-facing switch, light or valve. Use a unique `rc.id` for
each include. For example, this complete firmware describes a bare ESP32 with a relay on GPIO4;
it is not a pin map for an arbitrary retail product:

```yaml
substitutions:
  name: workshop-relay
  friendly_name: Workshop Relay

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - packages/boards/espressif/esp32dev.yaml
      - path: packages/modules/relay-control.yaml
        vars:
          rc:
            id: workshop
            entity:
              type: switch
              name: None
            power:
              pin: GPIO4
            power_cycle:
              enabled: true
              delay: 3s
```

| `rc` field | Default / meaning |
| --- | --- |
| `id` | `rc1`; unique prefix for infrastructure IDs. |
| `power.provider` | `gpio`; `external` instead uses an output you create. |
| `power.pin`, `power.inverted`, `power.strapping` | `GPIO0`, false, false; set the actual wiring. GPIO provider only. |
| `power.output_id` | `<id>_power_output`; required to identify the supplied output for an external provider. |
| `power.restore_mode` | `RESTORE_DEFAULT_OFF`; fallback for entity restore settings. |
| `control` | Same fields as `entity.control` below; entity fields take precedence. |
| `power_cycle.enabled`, `.name`, `.delay` | false, `Power Cycle`, `3s`. |

### Entity Fields

`rc.entity` is also the `entity` object accepted by single-relay devices:

| Field | Default / meaning |
| --- | --- |
| `enabled` | true; false leaves only the physical output, without state/command scripts or optional features. |
| `type` | `switch`; also `light` or `valve`. |
| `id` | `<rc.id>_power_relay`, `<rc.id>_control_light` or `<rc.id>_control_valve`, according to role. Hardware profiles may supply another default. |
| `name` | `None`, meaning device name; profiles can choose a channel name. |
| `icon` | Empty; use the native entity/device-class icon. |
| `internal`, `disabled_by_default` | false; hide from HA, or offer disabled in HA, respectively. |
| `restore_mode` | `RESTORE_DEFAULT_OFF`; native restore mode for the selected state owner. |
| `device_class` | Empty; valves can use `water` or `gas`. |
| `control.mode` | `local`; also `detached` (HA actions) or `none` (no action). |
| `control.entity_id` | Empty; HA target required for useful detached control. |
| `control.service_on`, `.service_off`, `.service_toggle` | `light.turn_on`, `light.turn_off`, `light.toggle`; change for another HA domain. |
| `power.exposed` | true for switches, false for lights/valves; separately exposes physical POWER when needed. |
| `power.id`, `.name`, `.icon`, `.disabled_by_default` | `<rc.id>_power_relay`, `Power`, empty, false for a separate backing switch. |
| `power.restore_mode` | Overrides `entity.restore_mode`, which overrides `rc.power.restore_mode`. |

A local light owns its output directly unless separate POWER exposure is requested. Valves and
other roles needing a backing switch keep restoration there. Do not assume a backing switch ID
exists for every role. `power.internal` at the `rc` level is a low-level override of backing-switch
visibility; prefer the entity's visibility and `entity.power.exposed` in consumer configurations.
Profile authors can set `rc.default_name`, `default_entity_id`, `default_enabled`,
`default_internal` and `default_disabled_by_default` without overriding explicit entity choices.

### Inputs And Indicators

| Object under `rc` | Fields and defaults |
| --- | --- |
| `indicator_led` | `enabled: false`, `pin: GPIO0`, `inverted: false`, `strapping: false`, `name: Relay LED`, `internal: true`. Follows physical POWER. |
| `integrated_button` | `enabled: false`, `pin: GPIO0`, `inverted: true`, `strapping: false`, `name: Integrated Button`, `internal: false`. Toggles physical POWER. |
| `external_switch` | `enabled: false`, `pin: GPIO0`, `inverted: false`, `strapping: false`, `name: External Switch`, `mode: rocker`, `startup_delay: 1s`. `momentary` toggles on press; `rocker` toggles on either edge. Initial publication is ignored. |
| `external_magic` | `enabled: false`, `source_id: external_magic_source`, `state_internal: false`. Requires an existing binary sensor that emits presses, for example from a Magic Switch component. |

External inputs operate PRIMARY (the selected entity/control target). Detached HA control needs
an API connection and permission to perform HA actions. Physical POWER remains independently
controllable. Setting a detached target does not turn the physical relay into an HA state mirror.

Stable integration points for enabled instances:

- `<id>_power_output`: physical binary output.
- `<id>_power_state`: internal binary sensor, independent of the selected state owner.
- `<id>_power_on`, `_power_off`, `_power_toggle`: scripts for the physical output/state owner.
- `<id>_primary_on`, `_primary_off`, `_primary_toggle`: scripts for the selected entity.
- `<id>_after_power_on`, `_after_power_off`, `_after_power_change`: scripts you may extend with
  device-specific state hooks.
- `<id>_power_cycle`: script when power cycling is enabled.

## Pins

[`pin.yaml`](pin.yaml) is an inline GPIO schema include, not a `packages` entry. The board supplies
`firmware_platform`/`firmware_family`; the wrapper emits only fields that platform accepts.

```yaml
pin: !include
  file: ../packages/modules/pin.yaml
  vars:
    pin:
      number: GPIO4
      inverted: false
      mode:
        output: true
```

`pin.schema` is `gpio` (default) or `number`. GPIO fields are `number` (default GPIO0, normally
always set it), `inverted` (false), `allow_other_uses` (false), and `mode.input`, `output`, `pullup`,
`pulldown`, `open_drain` (all false). ESP32-only fields are `drive_strength` (20mA),
`ignore_strapping_warning` (false) and `ignore_pin_validation_error` (false); they are omitted on
ESP8266 and LibreTiny. Native platform validation still decides which pins/modes are legal.
`schema: number` omits GPIO mode/inversion fields for consumers such as Ethernet. This wrapper
does not create GPIO expanders or IDs and can be included as many times as needed.

## Energy Monitoring

Include **one energy monitor per firmware**. Both modules use fixed IDs `energy_monitor`, `voltage`,
`current`, `power` and `energy`; BL0942 also uses `frequency`. Including both modules or either
twice causes collisions. They do not own relays or protection logic.

| Module | `energy` fields and defaults |
| --- | --- |
| [BL0937](energy-monitoring-bl0937.yaml) | `cf_pin: GPIO6`, `cf1_pin: GPIO8`, `sel_pin: GPIO11`, `voltage_divider: 775`, `current_resistor: 0.00104 ohm`, `current_multiply: 1`, `update_interval: 30s`. |
| [BL0942](energy-monitoring-bl0942.yaml) | `tx_pin: GPIO11`, `rx_pin: GPIO10`, `baud_rate: 4800`, `update_interval: 30s`. Creates its UART. |

Calibration and pins in complete device packages can override module defaults. An `energy` object
is not permission to change unmeasured electrical characteristics or to share an occupied UART.

## QWater Meters

[`wmbus/qwater-meter.yaml`](wmbus/qwater-meter.yaml) accepts `meter.id` (default `water_meter`),
`name` (`Water`), `meter_id` (required radio ID), and `radio_id` (`radio_transceiver`). The receiver
must already provide that `wmbus_radio` and the external wMBus components; the complete wMBus device
does so. Each include registers the QWater driver automatically.

Every generated ID is prefixed by `meter.id`, so multiple meters are supported. Volume is m3;
derived consumption is litres. End-of-month/year dates are date entities. Last Update is a UTC
timestamp; the meter's timezone-free local clock remains text. See the
[complete dashboard example](../../devices/README.md#wmbus).

## Behavior Helpers

Complete devices already include the helpers they need. You only need these APIs when composing
your own firmware. Each example below is an entry in a remote package's `files:` list:

```yaml
packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: packages/modules/relay-group.yaml
        vars:
          relay_group:
            id: sockets
            members: [desk, printer]
            indicator_id: socket_led
```

This example requires an existing board package, relay-control instances `desk` and `printer`
with power cycling enabled, and a light with ID `socket_led`. It does not define physical hardware.

## Relay Groups

[`relay-group.yaml`](relay-group.yaml) combines existing relay-control members. It reports whether
any member is powered, updates the supplied indicator light, and provides an all-off/all-on toggle
and a power-cycle button. A physical button can call `script.execute: sockets_toggle`.

| `relay_group` field | Default | Meaning |
| --- | --- | --- |
| `id` | Required | Unique prefix for the group's command and button IDs. |
| `members` | Required | Nonempty list of unique relay-control `rc.id` values, in command order. |
| `indicator_id` | Required | Existing light ID; the group controls this light at boot and on state changes. |
| `state_id` | `<id>_power_status` | Aggregate binary sensor ID. |
| `state_name` | Power Status | Aggregate entity name. |
| `cycle_name` | Reboot All Relays | Power-cycle button name. |

Members must provide their POWER state and on/off/cycle scripts. Do not include disabled relay
entities or members without `rc.power_cycle.enabled: true`. The group operates physical POWER,
not detached HA targets. It does not create relays, alter restore modes or change per-member cycle
delays. Power cycles start consecutively without waiting for each cycle to finish.

Generated IDs are `<id>_toggle`, `<id>_cycle` (a button), and `state_id`. Multiple groups are
supported: use distinct IDs, entity names and indicator lights. State is sampled by the template
sensor as in the power-strip devices; this is not a safety interlock or an atomic multi-relay command.

## Fan Power Facade

[`fan-power-sync.yaml`](fan-power-sync.yaml) exposes a template fan backed by an existing power
switch. It writes power only when the switch differs from the requested state. An OFF command does
not send speed or oscillation commands. An ON command sends power first, then runs `on_running`.
It does not wait for MCU acknowledgement before those actions.

```yaml
- path: packages/modules/fan-power-sync.yaml
  vars:
    fan_sync:
      id: room_fan
      power_id: fan_power
      speed_count: 2
      name: Ventilation
      command_condition:
        lambda: return !id(syncing_from_mcu);
      on_running:
        - lambda: |-
            // The device defines this number and its protocol mapping.
            auto call = id(fan_speed_command).make_call();
            call.set_value(x->speed);
            call.perform();
```

This example assumes `fan_power`, `syncing_from_mcu` and `fan_speed_command` already exist.
`on_running` receives the native fan `on_state` argument `x` (`fan::Fan *`). Read it immediately
when taking a command snapshot; delayed actions see the fan's later state.

| `fan_sync` field | Default | Meaning |
| --- | --- | --- |
| `id` | Required | Fan ID. |
| `power_id` | Required | Existing switch ID. Hide the backing switch in your device when appropriate. |
| `speed_count` | Required | Number of supported speeds, validated by ESPHome's template fan. |
| `on_running` | Required | Action list for speed/oscillation commands; `[]` is allowed. |
| `name` | Empty | Fan entity name; empty uses the device name in HA. |
| `has_oscillating` | `false` | Advertise oscillation capability; the device must implement it. |
| `restore_mode` | `RESTORE_DEFAULT_OFF` | Native ESPHome fan restore mode. |
| `command_condition` | Always true | Native ESPHome condition checked before any power or running action. |

The module creates only the fan with the supplied ID. Multiple independent instances are supported.
It does not create datapoints or MCU listeners. The device must publish readback to the fan and
implement any feedback guard, boot-speed policy, invalid-value handling and speed/oscillation mapping.
It also owns modes, humidity settings, fault entities and their control/configuration categories.

Pro Breeze and JUMMICO deliberately retain different readback policies. Pro Breeze reflects low speed
after power-on and maps enum 0 to high. JUMMICO maps enum 0 to low, ignores unavailable speed reports,
and blocks outgoing commands while applying MCU readback. Physical JUMMICO swing remains local-only.

## CT16 Channels

[`tuya-ct16-channel.yaml`](tuya-ct16-channel.yaml) is the product-specific channel profile used 16
times by `devices/tuya-ct-clamp-16em-200a.yaml`. It is not a generic Tuya energy-meter decoder.
Normal dashboard users should include that device and use its `c01_name` through `c16_name`,
corresponding `_internal` substitutions, `sol_internal`, and `energy_scale`.

Its `ct16_channel` fields are `number` (required integer 1..16), `name` (required), `tuya_id`
(required existing MCU ID), `energy_scale` (required), `internal` (default false), and
`solar_internal` (default false). It creates energy from DP `114 + number`, current, power, CT
presence and solar-mode entities. Energy remains kWh with two decimal places and a nonnegative
clamp; the caller supplies its multiplier. Hidden channels remain available to the decoder.

The device owns raw payload decoding, phase/total measurements, configuration queries, and timing.
Decoder targets remain `circuit_<number>_current`, `_power`, `_ct_detected` and `_solar_configured`.
Each channel number may occur once; these fixed IDs support one CT16 meter per firmware.
