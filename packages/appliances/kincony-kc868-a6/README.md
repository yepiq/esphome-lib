# KinCony KC868-A6

This appliance package targets the original ESP32-based KinCony KC868-A6. It does not target the
later ESP32-S3-based KC868-A6v3, which has a different pin map and peripheral implementation.

The appliance owns the fixed board wiring and exposes six relays, six dry-contact inputs, four
0-5 V analog inputs, two 0-10 V analog outputs, RS485, RS232, SPI, I2C, two OneWire-capable ports,
and the DS1307 RTC. Applications own Modbus or other serial protocols, attached SPI/OneWire devices,
and input-to-relay automations.

## Hardware

- original ESP32 MCU
- six active-low relays through a PCF8574 at address `0x24`
- six active-low dry-contact inputs through a PCF8574 at address `0x22`
- four 0-5 V analog inputs
- two 0-10 V analog outputs
- RS485 and RS232 transceivers
- DS1307 RTC
- SPI expansion header and two GPIO32/GPIO33 sensor ports

KinCony rates the relay contacts at up to 10 A at 277 V AC. Installation and load selection must
follow the manufacturer's electrical-safety guidance.

## Pin Map

| Function | ESP32 / expander pin |
| --- | --- |
| Analog inputs 1-4 | GPIO36, GPIO39, GPIO34, GPIO35 |
| Analog outputs used by this profile | Output 1 GPIO25, Output 2 GPIO26 |
| OneWire-capable ports 1-2 | GPIO32, GPIO33 |
| I2C SDA / SCL | GPIO4 / GPIO15 |
| Digital inputs 1-6 | Input PCF8574 pins 0-5 at `0x22` |
| Relays 1-6 | Output PCF8574 pins 0-5 at `0x24` |
| RS485 TX / RX | GPIO27 / GPIO14 |
| RS232 TX / RX | GPIO17 / GPIO16 |
| SPI SCLK / MOSI / MISO | GPIO18 / GPIO23 / GPIO19 |
| SPI chip select | GPIO5, available to the consuming component |

KinCony's published pin definition calls GPIO26 `DAC1` and GPIO25 `DAC2`, while ESP32's native DAC
channel numbering is the reverse. This profile deliberately preserves its established mapping of
the `Analog Output 1` entity to GPIO25 and `Analog Output 2` to GPIO26. Changing that mapping is a
separate behavioral decision, not part of the package refactor.

## Usage

For the ESPHome dashboard, start with a complete remote include:

```yaml
substitutions:
  name: io-controller
  friendly_name: IO Controller

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: packages/appliances/kincony-kc868-a6.yaml
        vars:
          kincony_kc868_a6:
            rs485:
              baud_rate: 19200
              parity: EVEN
            relays:
              relay1:
                entity:
                  type: valve
                  name: Garden Valve
                  device_class: water
```

Include this appliance once per firmware. It supplies the board and fixed peripheral buses;
do not include an additional board package. The following local example shows further overrides.

The defaults expose every channel, use Wi-Fi, configure both serial ports as 9600-8-N-1, preserve
the existing relay-switch `RESTORE_DEFAULT_OFF` behavior, poll analog inputs every second, and
restore analog output values.

```yaml
packages:
  - !include
    file: ../packages/appliances/kincony-kc868-a6.yaml
    vars:
      kincony_kc868_a6:
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
              restore_mode: RESTORE_DEFAULT_ON
          relay3:
            entity:
              type: valve
              name: Irrigation Valve
              device_class: water
          relay6:
            entity:
              enabled: false
        digital_inputs:
          input1:
            id: controller_digital_input_1
            name: Pump Feedback
        analog_inputs:
          input1:
            name: Pressure
            update_interval: 5s
        analog_outputs:
          output1:
            name: Demand
```

Every relay always creates a physical binary output. Its `output_id` defaults to `r1_output` through
`r6_output`. The shared relay-control framework creates a user-facing entity by default with ids
`r1` through `r6`. Configure that facade under `entity`:

- `enabled`: create the facade; defaults to `true`
- `type`: `switch` (default), `light`, or `valve`
- `id`, `name`, `icon`, `internal`, and `disabled_by_default`: entity identity and visibility
- `restore_mode`: restored power-state policy; defaults to `RESTORE_DEFAULT_OFF`
- `device_class`: optional `water` or `gas` class for valve entities

Set `entity.enabled: false` when an application consumes the physical output through its own
component or controller capability. The output remains present; the consuming application then owns
state and restoration. Existing flat `enabled`, `id`, `name`, `internal`, `disabled_by_default`, and
`restore_mode` fields remain fallback values for existing callers, while nested `entity` fields take
precedence.

Channel fields are not interchangeable:

| Channel object | Accepted fields |
| --- | --- |
| `digital_inputs.input1` through `input6` | `enabled`, `id`, `name`, `internal`, `disabled_by_default` |
| `analog_inputs.input1` through `input4` | `enabled`, `name`, `internal`, `disabled_by_default`, `update_interval` (default `1s`) |
| `analog_outputs.output1` through `output2` | `enabled`, `name`, `internal`, `disabled_by_default`, `restore_value` (default `true`) |

`enabled` defaults to `true`; `internal` and `disabled_by_default` default to `false`.
Setting `enabled: false` removes that complete input or analog channel. Analog IDs are fixed:
`ai1` through `ai4`, `ao1`/`ao2`, and their `ao1_dac`/`ao2_dac` backing outputs. There is no analog
`id` override in this API.

Both `rs485` and `rs232` accept `id`, `baud_rate` (9600), `data_bits` (8), `parity` (`NONE`) and
`stop_bits` (1). `rtc` accepts `id` (default `rtc_time`). `networking` accepts the shared
[networking object](../../modules/networking/README.md). The board owns all physical pins.
Pass optional original-ESP32 `esp32_advanced` alongside `kincony_kc868_a6`, not inside it.

Existing infrastructure IDs are preserved for compatibility:

- relay outputs `r1_output` through `r6_output`, configurable with `relays.relayN.output_id`
- default relay facade ids `r1` through `r6`, configurable with `relays.relayN.entity.id`
- digital inputs `di1` through `di6`
- analog inputs `ai1` through `ai4`
- analog output numbers `ao1` and `ao2`, backed by `ao1_dac` and `ao2_dac`
- UARTs `rs485` and `rs232`
- OneWire buses `ow_bus1` and `ow_bus2`
- expanders `inputs` and `outputs`, and RTC `rtc_time`

Set `rs485.id`, `rs232.id`, `rtc.id`, or a digital input's `id` when a consuming application needs
stable capability-oriented identifiers such as `controller_rs485_uart`, `controller_rtc`, and
`controller_digital_input_1`.

Sources:

- [KinCony KC868-A6 pin definition](https://www.kincony.com/forum/showthread.php?tid=1962)
- [KinCony KC868-A6 hardware design](https://www.kincony.com/kc868-a6-hardware-design-details.html)
- [KinCony controller specifications](https://www.kincony.com/download/KC868-Smart-Controller-parameters-v3.2.pdf)
