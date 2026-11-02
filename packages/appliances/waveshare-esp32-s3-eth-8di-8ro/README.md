# Waveshare ESP32-S3-ETH-8DI-8RO

This appliance package targets the Waveshare `ESP32-S3-ETH-8DI-8RO` RS485 relay controller. It
owns the board's fixed wiring and exposes relays, isolated digital inputs, Ethernet, RTC, RS485,
RGB LED, buzzer output, and boot button. Applications own Modbus or other RS485 protocols and all
input-to-relay automations.

Do not use this profile for the similarly named `8DI-8DO`, `8DI-8RO-C`, or CAN variants without a
complete pin-map comparison.

## Hardware

- ESP32-S3-WROOM-1U-N16R8: 16 MB flash and 8 MB octal PSRAM
- W5500 SPI Ethernet controller
- TCA9554PWR 8-bit I/O expander at address `0x20`
- eight active-high relay outputs, each with one normally-open and one normally-closed contact
- eight optocoupler-isolated digital inputs for active or passive contacts
- isolated RS485 interface
- PCF85063ATL RTC at address `0x51`
- one WS2812 RGB LED and one PWM buzzer
- 7-36 V DC input or 5 V USB-C power

Waveshare rates the relay contacts at up to 10 A at 250 V AC or 10 A at 30 V DC. Installation and
load selection must follow the manufacturer's electrical-safety guidance.

## Pin Map

| Function | ESP32-S3 / expander pin |
| --- | --- |
| Digital inputs 1-8 | GPIO4-GPIO11 |
| W5500 interrupt | GPIO12 |
| W5500 MOSI | GPIO13 |
| W5500 MISO | GPIO14 |
| W5500 clock | GPIO15 |
| W5500 chip select | GPIO16 |
| W5500 reset | GPIO39 |
| RS485 TX / RX | GPIO17 / GPIO18 |
| RGB LED | GPIO38 |
| RTC interrupt | GPIO40, not consumed by this package |
| I2C SCL / SDA | GPIO41 / GPIO42 |
| Buzzer | GPIO46 |
| Boot button | GPIO0 |
| Relays 1-8 | TCA9554 pins 0-7 |

## Usage

For an ESPHome dashboard configuration:

```yaml
substitutions:
  name: ethernet-controller
  friendly_name: Ethernet Controller

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: packages/appliances/waveshare-esp32-s3-eth-8di-8ro.yaml
        vars:
          waveshare_8di8ro:
            relays:
              relay1:
                entity:
                  type: valve
                  name: Garden Valve
                  device_class: water
```

Use one appliance per firmware; it supplies the board and fixed buses. Parameters belong in the
`waveshare_8di8ro` object. Besides channel fields below, it accepts `networking`
([shared settings](../../modules/networking/README.md), Ethernet by default), `rs485.id`,
`rs485.baud_rate` (9600), `rs485.data_bits` (8), `rs485.parity` (NONE), `rs485.stop_bits` (1),
and `rtc.id`. Pins, expanders and onboard RGB/buzzer hardware are not selectable profiles.

The defaults expose all relay and digital-input channels, use Ethernet, and configure RS485 as
9600-8-N-1. Relay switch facades use `ALWAYS_OFF` so every firmware boot starts with all loads off.

```yaml
packages:
  - !include
    file: ../packages/appliances/waveshare-esp32-s3-eth-8di-8ro.yaml
    vars:
      waveshare_8di8ro:
        networking:
          mode: ethernet # ethernet | wifi
        rs485:
          id: controller_rs485_uart
          baud_rate: 19200
          parity: EVEN
        rtc:
          id: controller_rtc
        relays:
          relay1:
            output_id: controller_relay_1
            entity:
              enabled: false
          relay2:
            entity:
              type: light
              name: Pump
              restore_mode: RESTORE_DEFAULT_OFF
          relay3:
            entity:
              type: valve
              name: Irrigation Valve
              device_class: water
          relay8:
            entity:
              enabled: false
        digital_inputs:
          input1:
            id: controller_digital_input_1
            name: Pump Feedback
          input8:
            enabled: false
```

Every relay always creates a physical binary output. Its `output_id` defaults to
`waveshare_8di8ro_relay_1_output` through `waveshare_8di8ro_relay_8_output`. The shared
relay-control framework creates a user-facing entity by default with the corresponding id without
the `_output` suffix. Configure that facade under `entity`:

- `enabled`: create the facade; defaults to `true`
- `type`: `switch` (default), `light`, or `valve`
- `id`, `name`, `icon`, `internal`, and `disabled_by_default`: entity identity and visibility
- `restore_mode`: restored power-state policy; defaults to `ALWAYS_OFF`
- `device_class`: optional `water` or `gas` class for valve entities

Set `entity.enabled: false` when an application consumes the physical output through its own
component or controller capability. The output remains present; the consuming application then owns
state and restoration. Existing flat `enabled`, `id`, `name`, `internal`, `disabled_by_default`, and
`restore_mode` fields remain fallback values, while nested `entity` fields take precedence.

Each `digital_inputs.input1` through `input8` object accepts `enabled`, `id`, `name`, `internal`,
`disabled_by_default`, and `use_interrupt`. Setting `enabled: false` removes that digital input.

Network mode is a package variable and cannot be selected with an `esphome run` command-line
option. A local wrapper that selects Wi-Fi looks like this:

```yaml
substitutions:
  name: waveshare-8di8ro-test
  friendly_name: Waveshare 8DI 8RO Test

packages:
  - !include
    file: devices/waveshare-esp32-s3-eth-8di-8ro.yaml
    vars:
      waveshare_8di8ro:
        networking:
          mode: wifi
```

Run that wrapper normally with `esphome run <wrapper>.yaml`. Wi-Fi mode requires `wifi_ssid` and
`wifi_password` in the wrapper's `secrets.yaml`.

The isolated inputs are electrically active-low at the ESP32 and are inverted by the appliance so
an active input is reported as `ON`.

Stable infrastructure IDs are:

- relay outputs `waveshare_8di8ro_relay_1_output` through `waveshare_8di8ro_relay_8_output`
- default relay facade ids `waveshare_8di8ro_relay_1` through `waveshare_8di8ro_relay_8`
- `waveshare_8di8ro_input_1` through `waveshare_8di8ro_input_8`
- `waveshare_8di8ro_rs485_uart`
- `waveshare_8di8ro_i2c` and `waveshare_8di8ro_rtc`
- `waveshare_8di8ro_rgb_led`
- `waveshare_8di8ro_buzzer` and `waveshare_8di8ro_buzzer_output`
- `waveshare_8di8ro_boot_button`

Set `rs485.id`, `rtc.id`, a relay's `output_id`, or a digital input's `id` when a consuming
application needs capability-oriented identifiers such as `controller_rs485_uart`,
`controller_rtc`, `controller_relay_1`, and `controller_digital_input_1`.

Sources:

- [Waveshare product wiki](https://www.waveshare.com/wiki/ESP32-S3-ETH-8DI-8RO)
- [ESPHome W5500 Ethernet](https://esphome.io/components/ethernet/)
- [ESPHome PCA9554/TCA9554 support](https://esphome.io/components/pca9554/)
- [ESPHome PCF85063 support](https://esphome.io/components/time/pcf85063/)
