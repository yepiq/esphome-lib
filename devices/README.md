# Device Reference

Include one device package in your ESPHome dashboard configuration and select the hardware profile
that matches the installed module. A profile selects real wiring and MCU capabilities, not just a
display name. Unsupported profiles fail configuration.

Set `name` and `friendly_name` in your dashboard. When migrating an installed device, keep its
existing values to preserve its network identity and Home Assistant presentation.

## Tuya CT Clamp 2EM 80A

One firmware definition supports CB2S and T1-M versions of this two-channel Tuya MCU meter.
Both use the same telemetry datapoints and scaling; only the T1-M profile exposes its additional
alarm settings, buzzer and diagnostic alarm entities. Each variant's cloud model remains a
separate JSON file under `data-models/tuya/things-data-model/`.

```yaml
substitutions:
  name: grid-monitor
  friendly_name: Grid Monitor

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: devices/tuya-ct-clamp-2em-80a.yaml
        vars:
          ct_clamp:
            profile: t1m
            channels:
              a_name: Grid
              b_name: Solar
```

The `ct_clamp` include object accepts:

| Field | Default | Accepted Values |
| --- | --- | --- |
| `profile` | `cb2s` | `cb2s`, `t1m` |
| `channels.a_name` | `Channel A` | Channel A's label in entity names |
| `channels.b_name` | `Channel B` | Channel B's label in entity names |

These established dashboard substitutions also remain available:

| Substitution | Default | Meaning |
| --- | --- | --- |
| `uart_tx_pin`, `uart_rx_pin` | `GPIO11`, `GPIO10` | Tuya MCU UART pins |
| `uart_baud_rate` | `9600` | Tuya MCU UART baud rate |
| `channel_a_name`, `channel_b_name` | From `ct_clamp.channels` | Direct channel-label override |
| `power_scale` | `0.1` | Raw power to watts |
| `energy_scale` | `0.01` | Raw energy to kWh |
| `frequency_scale` | `0.01` | Raw frequency to Hz |
| `voltage_scale` | `0.1` | Raw voltage to volts |
| `current_scale` | `0.001` | Raw current to amperes |

The device uses the shared Home Assistant clock, `ha_time`, for Tuya MCU time. Disabling that clock
requires you to provide another time component with that ID; the device cannot simply drop its
time dependency. Its telemetry IDs and T1-M alarm IDs are unchanged across hardware profiles.

## Tuya Strip 4PM

The `cbu` and `t1u` profiles each provide four switched sockets, a switched USB supply and a BL0942
energy monitor. Their physical button switches all five relays off when any is on, or all on when
all are off. The status LED follows aggregate relay state. Each relay retains its power-cycle
button, and `Reboot All Relays` operates all five.

```yaml
substitutions:
  name: office-power-strip
  friendly_name: Office Power Strip

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: devices/tuya-strip-4pm.yaml
        vars:
          power_strip:
            profile: t1u
```

The `power_strip` include object accepts `profile`, either `cbu` (default) or `t1u`.
Established dashboard substitutions remain available:

| Substitution | Default | Meaning |
| --- | --- | --- |
| `relay1_id` through `relay4_id` | `socket_1` through `socket_4` | Relay-control ID prefixes |
| `relay5_id` | `relay_usb` | USB relay-control ID prefix |
| `relay1_name` through `relay4_name` | `Socket 1` through `Socket 4` | Entity names |
| `relay5_name` | `Relay USB` | USB entity name |
| `relay1_pin` through `relay5_pin` | Profile wiring | Physical relay GPIOs |
| `relay1_inverted` through `relay5_inverted` | `false` | Relay polarity |
| `led_pin` | Profile wiring | Status LED GPIO |
| `led_inverted` | `false` | Status LED polarity |
| `button_pin` | `GPIO22` | Physical master button GPIO |
| `button_pullup`, `button_inverted` | `true`, `true` | Button electrical configuration |

The BL0942 module's `energy` include object is forwarded unchanged; its serial defaults are TX
GPIO11, RX GPIO10, 4800 baud and a 30-second update interval. It accepts `tx_pin`, `rx_pin`,
`baud_rate` and `update_interval`. Changing pin overrides requires matching physical wiring.

## Tuya Thermostat 716

This initial profile targets the discrete BK7231N on the main PCB and a separate Tuya MCU.
The firmware dump confirms BK7231N and contains the same datapoint schema as the archived
[Things Data Model](../data-models/tuya/things-data-model/tuya-thermostat-716.json).
UART1 TX GPIO11/RX GPIO10 at 9600 baud is provisional until board tracing or MCU logs confirm it.

```yaml
substitutions:
  name: room-thermostat
  friendly_name: Room Thermostat
  uart_baud_rate: 9600

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - devices/tuya-thermostat-716.yaml
```

`uart_tx_pin`, `uart_rx_pin`, and `uart_baud_rate` are dashboard substitutions. The primary
climate exposes Off/Heat and Schedule/Manual presets. It waits for MCU feedback and sends no
restored climate settings at boot. Valve activity comes from read-only DP36, including heating
reported while power is off. A template climate avoids ESPHome 2026.10's native Tuya climate
writing to its `active_state` datapoint when Heat is selected.

Temperature values use the cloud model's factor of 0.1. The advertised setpoint range is
5–300 °C in 0.5 °C steps; upper/lower limit controls also retain the 300 °C cloud ceiling.
These are provisional cloud ranges, not hardware-verified limits. Temperature Unit is treated
as a display setting; verify whether changing it affects MCU wire values. Reported adjustment
steps and the supported-features bitmask are diagnostic entities; they do not yet change entity
availability or control steps dynamically.

Protection switches, sensor mode, calibration, switching differential, temperatures, battery
and fault diagnostics are included. Battery values outside 0–100 report unavailable. External
Sensor Type Code remains read-only until its numeric mapping is known. External Temperature
and Window Open are observations even though the model marks them writable. Weekly schedule,
backlight/night-mode and towel-rail configuration are read-only raw hex diagnostics, disabled
by default; editing these payloads requires captured MCU examples. The device uses `ha_time`
for the MCU clock, so disabling the shared HA clock requires another clock with that ID.

## Shared Settings

Both families inherit logger defaults. Set `substitutions.log_level` or your dashboard's `logger`
configuration to change verbosity. Neither device adds a release-version bump for a hardware
profile selection.

Pass the [networking object](../packages/modules/networking/README.md) under the device include's
`vars` for network/service settings. Additional minimum ESPHome requirements use the
[additive requirements list](../packages/README.md), not a direct `esphome.min_version` override.

The same identity/logging convention applies to all devices. On ESP32 targets,
`vars.esp32_advanced.flash_chip` selects the flash vendor driver using the value recommended by
that device's boot log. It has no library default; do not assume every board uses the same vendor.
For example, a device reporting `Set flash_chip: winbond` can use:

```yaml
vars:
  esp32_advanced:
    flash_chip: winbond
```

For original ESP32 targets only, the same object also accepts `minimum_chip_revision` and
`sram1_as_iram`; neither has a library default. Do not use those two options on ESP32-C3/S3, or any
of these ESP32 options on ESP8266 or LibreTiny targets. Keep hardware-specific serial logging
disabled where the package requires it.

## Relay Devices

Sonoff BASIC R4/MINIR4, Tuya Mini Switch 1DC/1PM, Relay 1PM 30A and the single-socket profiles
accept `vars.entity`. This is the [relay-control entity object](../packages/modules/README.md#relay-control),
not a native ESPHome entity block. It accepts `type`, `enabled`, `id`, `name`, `icon`, `internal`,
`disabled_by_default`, `restore_mode`, `device_class` (valves), `power` and `control`.
The default role is a switch named after the device.

```yaml
substitutions:
  name: dining-switch
  friendly_name: Dining Switch

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: devices/tuya-mini-switch-1dc-5a.yaml
        vars:
          entity:
            power:
              restore_mode: RESTORE_DEFAULT_ON
            control:
              mode: detached
              entity_id: light.dining
```

Detached control requires permission for the ESPHome device to perform Home Assistant actions.
The physical integrated button still operates local POWER; the external wall-switch input operates
the selected control target. `entity.enabled: false` removes the entity and its control features,
but leaves the physical output available for your own application.

The 2DC dry relay accepts `relay_1_entity` and `relay_2_entity`; the 4DC accepts those plus
`relay_3_entity` and `relay_4_entity`. Each uses the same entity schema. The 4DC also accepts
`enabled_channels` (default `[1, 2, 3, 4]`) to select exposed channels. Both dry-relay devices' optional `rf433`
object accepts `enabled` (false), `buffer_size` (16kb), `filter` (150us) and `idle` (4ms).
ESPHome 2026.10 interprets the buffer as bytes on these LibreTiny devices. The new default preserves
the previous pulse capacity. Multiply an existing custom pre-2026.10 buffer value by four to keep
its former capacity; explicit values are passed through as bytes.

The 3x2 strip uses substitutions `relay1_id` through `relay4_id` (defaults `socket_1_2`,
`socket_3_4`, `socket_5_6`, `relay_usb`) and corresponding `relay1_name` through `relay4_name`.
Defaults are `Socket 1&2`, `Socket 3&4`, `Socket 5&6`, `Relay USB`. Its physical button and status
LED aggregate all four outputs. See the [4PM family](#tuya-strip-4pm) for the five-output model.

### BASIC R4 Magic Switch

`entity.magic_switch` accepts the following timing options. These are sensor-detection settings,
not a request to change mains wiring. See the [component reference](../components/magic_switch/README.md).

| Field | Default |
| --- | --- |
| `min_pulse`, `max_pulse` | `1ms`, `120ms` |
| `detect_missing_pulses` | `false` |
| `adaptive_min_pulse`, `adaptive_margin` | `750us`, `200us` |
| `phase_tolerance` | `1ms` |
| `recovery_pulses`, `recovery_timeout` | `2`, `150ms` |
| `startup_mask`, `debounce`, `relay_mask` | `2s`, `250ms`, `500ms` |
| `dnd.enabled`, `dnd.name` | `false`, `Do Not Disturb` |

## Garage Opener

The opener has one closed-position contact. CLOSED is contact-confirmed; OPEN means not closed,
not a measured fully open endpoint. Commands use this contact even after a reboot or an external
remote operation. Travel time bounds the movement guard; a closing timeout leaves the door reported
as not closed and allows another explicit CLOSE command. Set travel time for the actual installation
and retain the opener's physical safety systems. From a partial stop, relay-toggle direction depends
on the opener.

| Substitution | Default |
| --- | --- |
| `pulse_duration` | `0.2s` |
| `magnetic_contact_delay` | `0.5s` |
| `door_travel_time` | `30` seconds, initial value of the restored setting |
| `led_pin`, `button_pin`, `relay_pin`, `magnetic_pin` | `GPIO6`, `GPIO7`, `GPIO8`, `GPIO26` |

Optional BLE uses `vars.ble`: `enabled` (false), `name` (derived from friendly name and truncated
to fit advertising), `name_add_mac_suffix` (false), `connection_timeout` (5s). The established
`ble_enabled`, `ble_name`, `ble_name_add_mac_suffix` and `ble_connection_timeout` substitutions
also work. Enabling BLE requires `tuya_garage_opener_ble_command` in `secrets.yaml`.
The [BLE component](../components/bk72xx_ble_server/README.md) describes the protocol and limitations.

## Other Meters

These settings are substitutions unless explicitly called include vars. Calibration values are
product-specific: change them only from measurements or verified protocol information.
Fixed wiring and further electrical overrides are listed in each device's opening substitutions.

| Device | Parameters and defaults |
| --- | --- |
| EARU | `internal_update_interval: 1s` for BL0942 acquisition; `temperature_update_interval: 1s` for protection samples; `external_update_interval: 10s` for reporting. `temp_adc_scale: 100`; `relay_pulse_duration: 60ms`. See YAML for pin names. |
| CT3 | Include var `tuya_uart_baud_rate: 115200`; some hardware needs 9600. Scales: `voltage_scale: 0.1`, `current_scale: 0.001`, `power_scale: 0.001`, `power_factor_scale: 0.01`, `energy_scale: 0.01`, `frequency_scale: 0.01`. |
| CT16 | `phA_name`/`phB_name`/`phC_name`: Phase A/B/C; `c01_name` through `c16_name`: C01 through C16. Corresponding `_internal` flags and `sol_internal`: false. `voltage_scale: 0.1`, `current_scale: 0.001`, `power_scale: 1`, `freq_scale: 1`, `energy_scale: 0.01`. |
| Feyree EVSE, both products | `uart_tx_pin`, `uart_rx_pin`, `uart_baud_rate` (9600). Single-phase TX/RX GPIO17/GPIO16; three-phase PA14/PA13. `last_charge_energy_scale: 0.1`, `single_charge_energy_scale: 0.01`, `balance_energy_scale: 0.001`; `voltage_scale`, `current_scale`, `power_scale`, `temperature_scale`: 0.1. The two products are not interchangeable. |
| Water-quality 8-in-1 | `scale_temp: 0.1`, `scale_ph: 0.01`, `scale_pro: 0.001`, `scale_cf: 0.01`. |

EARU reports native kWh. Older firmware labeled the same numbers Wh; review existing HA energy
statistics before migrating an older installation. Faster acquisition does not imply faster HA
reporting, and software temperature protection is not a substitute for hardware protection.
CT16 inherits the shared Beken UART read guard and has no scheduled reboot. Its temporary
`UART RX Overflows` diagnostic counts incoming bytes discarded by a full software receive ring.
The total uses normal ESPHome preferences, surviving ordinary reboots and OTA reflashes;
recent unsaved events may be lost on abrupt power loss, and erasing preferences resets it.
The actual buffer remains 256 bytes while measuring overflow. See the
[UART guard component](../components/bk72xx_uart_guard/README.md) for the upstream removal condition
and the distinction between software-buffer drops and hardware UART errors.

## ESP-07 Serial Bridge

Include `devices/esp07-serial-bridge.yaml` and set `name` and `friendly_name` as usual.
The substitutions `uart_baud_rate` (115200) and `tcp_port` (6638) select the UART speed and
TCP listening port. UART framing is 8N1, with TX on GPIO1 and RX on GPIO3. Set the adapter's
switch to UART and cross TX/RX to the target, with a shared ground.

Wi-Fi uses the usual `wifi_ssid` and `wifi_password` secrets. Home Assistant API, OTA and HA time
use the shared networking defaults. TCP/UART forwarding works without an HA connection or clock
sync, and connection-loss reboots remain disabled. Uptime publishes the boot timestamp after the
first HA time sync, giving Home Assistant its usual relative-time display. Until that sync, uptime
remains unknown; forwarding is already available. A later HA disconnect does not clear the timestamp.

Connect with `nc esp07-serial-bridge.local 6638` (substitute your chosen name or IP).
Native [UART TCP](https://esphome.io/components/uart_tcp/) carries raw TCP bytes with one client
connected at a time. UART data received while disconnected is discarded. The bridge does not use
Telnet or RFC2217; clients cannot change baud rate remotely. ESPHome serial logging is disabled,
but the ESP8266 ROM still transmits startup bytes on TX during reset.

## Climate And Air Quality

Pro Breeze, JUMMICO, SCHEEAIR Nova 100 and MT-29 need no product-specific include object for normal
use. Include the exact device and set its identity. Pro Breeze and JUMMICO expose the dehumidifier
as a fan, with product-specific modes, humidity targets and grouped fault diagnostics. JUMMICO's
physical swing button has no verified remote datapoint and is not advertised as remotely controllable.
The ESP-07 serial replacement targets are not firmware for the original Tuya wireless modules.

### MELcutter

Keep MELcutter and MELcutter V2 separate: they use different CN105 drivers and expose different
capabilities. Both accept `default_remote_temperature_entity` (default empty string), the initial
HA sensor entity ID used for external temperature. A restored text setting takes precedence after
first boot. The sensor must report Celsius.

MELcutter V2 exposes a native `Vertical Vane` selector (`Auto`, positions `1`–`5`, `Swing`) and
climate swing modes for off, vertical, horizontal, and both axes. Fixed horizontal vane positions
remain deferred until ESPHome provides a built-in horizontal selector.

For external temperature, allow the ESPHome integration to perform HA actions and provide
`script.get_sensor_value`. The firmware calls it with `entity_id` and expects response data
`{"value": <number>}`. This example belongs in Home Assistant's `scripts.yaml`, **not** ESPHome:

```yaml
get_sensor_value:
  alias: Get Sensor Value
  mode: parallel
  fields:
    entity_id:
      required: true
      selector:
        entity:
          domain: sensor
  sequence:
    - variables:
        raw: "{{ states(entity_id) }}"
    - if:
        - condition: template
          value_template: "{{ not is_number(raw) }}"
      then:
        - stop: Sensor unavailable or non-numeric
          error: true
    - variables:
        result:
          value: "{{ raw | float }}"
    - stop: Return sensor value
      response_variable: result
```

This uses HA's [script response mechanism](https://www.home-assistant.io/docs/scripts/#stopping-a-script-sequence).
Unavailable values cause an error instead of becoming a false zero-degree measurement. The firmware
polls every 30 seconds, validates the returned range, and eventually falls back to the unit's own
sensor when remote readings stop. Test the script response in HA as well as validating the firmware.

## RF Fan Control

`fan433.radio.profile` selects `lilygo` (default) or `esp32dev_cc1101`. Each `fan433.fans` item is
either a numeric address or an object with `address`, optional `id` and optional `name`. Defaults
are `fan_<four-digit-lowercase-hex>` and `Fan <four-digit-uppercase-hex>`.

```yaml
substitutions:
  name: ventilation
  friendly_name: Ventilation

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: devices/fan-control-433.yaml
        vars:
          fan433:
            radio:
              profile: lilygo
            fans:
              - address: 0x36F2
                name: Outlet
              - address: 0x7D5B
                name: Inlet
            combined:
              name: None
              members:
                - address: 0x36F2
                  direction: out
                - address: 0x7D5B
                  direction: in
```

The optional `combined` object accepts `id` (default `combined_fan`), `name` (default `None`),
and `members`. Members refer to declared addresses and set `direction: out` (default) or `in`.
Individual fans remain exposed; hide them with native `!extend` plus `internal: true` if desired.
Each individual fan has a `<fan_id>_synchronize` button. State is assumed, not confirmed by RF
feedback. Synchronization deliberately runs the fan to a known speed endpoint before restoring
the requested state.

Protocol substitutions:

| Fields | Defaults |
| --- | --- |
| `rf_frequency` | `433.92MHz` |
| `fan_short_us`, `fan_long_us`, `fan_gap_us`, `fan_repeat_count` | `400`, `1200`, `11900`, `4` |
| `fan_cmd_on`, `fan_cmd_off` | `0x0A`, `0x0D` |
| `fan_cmd_out_plus`, `fan_cmd_out_minus`, `fan_cmd_in_plus`, `fan_cmd_in_minus` | `0x0B`, `0x0C`, `0x0E`, `0x0F` |
| `fan_speed_count`, `fan_restore_mode`, `fan_command_pause` | `6`, `RESTORE_DEFAULT_OFF`, `100ms` |
| `fan_direction_out`, `fan_direction_in` | `FORWARD`, `REVERSE` |
| `fan_sync_direction`, `fan_sync_endpoint`, `fan_sync_saturation_count` | `out`, `min`, `6` |
| `rf_learn_window_ms`, `rf_learn_window_s` | `30000`, `30`; keep these equivalent |

## wMBus

Set `board_profile` to `heltec` (default) or `lilygo`, and include one meter profile per physical
meter. Each `meter.id` must be unique. The eight-digit radio meter ID is not the HA entity ID.

```yaml
substitutions:
  name: water-radio
  friendly_name: Water Radio
  board_profile: heltec

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - devices/wmbus.yaml
      - path: packages/modules/wmbus/qwater-meter.yaml
        vars:
          meter:
            id: main_water
            name: Water Main
            meter_id: 0x12345678
```

The [QWater profile](../packages/modules/README.md#qwater-meters) documents units and prerequisites.
Other meter types need their own driver and entities; adding QWater does not decode arbitrary meters.

## Other Hardware Profiles

| Device | Configuration |
| --- | --- |
| Vevor 7-in-1 | Substitutions `board_profile: lilygo` (`heltec` also supported) and `weather_station_frequency: 868.350Mhz`. Match the transmitter band. `receiver_version` is project metadata, not a calibration setting. |
| BLE advertising proxy | Include var `ble_proxy.board: esp32dev`; select a matching BLE-capable board package basename. `esp32_advanced` stays a sibling var, not a field inside `ble_proxy`. |
| Ceiling lights | V1 CBU and V2 CBU/WL2H are distinct pin profiles. V2's `chip` substitution can select `cbu` or `wl2h`; prefer the matching device filename. |
| Weather ePaper panel | `weather_entity: weather.openweathermap`, `forecast_update_min: 30`, `view_swap_s: 30`, `full_update_every: 30`. Needs HA weather state/forecast actions, action permission and matching display wiring. |
| Irrigation controller | Bench draft only. Loaded-output measurements and final button behavior are pending in the YAML; do not deploy it to unattended irrigation. |

Integrated board examples use their corresponding [appliance APIs](../README.md#hardware-appliances).
Appliances own physical wiring; applications supply LVGL pages, Modbus controllers/registers or
radio protocol logic as appropriate. Do not add another board package to an appliance-based device.

## Entity Roles

- Primary entity: the device's main switch, light, fan, cover or climate entity. A name of `None`
  uses the device name; it is intentional, not a placeholder.
- Everyday controls: modes, targets and actions used during normal operation, without a config
  or diagnostic category.
- Configuration: tuning and persistent preferences, using `entity_category: config`.
- Diagnostics: faults, identification and service measurements, using `entity_category: diagnostic`.

`internal: true` removes an entity from HA; `disabled_by_default: true` lets HA offer it disabled
until you enable it. These are different from the entity category. Device-specific exceptions are
visible in the YAML. Native ESPHome `!extend` overrides can customize entities without changing the
package; preserve their IDs when doing so.
