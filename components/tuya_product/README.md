# Tuya Product Information

`tuya_product` captures the product-information response sent by a Tuya MCU during startup and
publishes its useful fields as ESPHome text sensors.

The Tuya Wi-Fi module requests this information with command `0x01`. A typical MCU response contains
JSON such as:

```json
{"p":"tehjajiyfp2phy4d","v":"1.0.14","m":0}
```

The component exposes:

| JSON field | Text sensor | Example |
| --- | --- | --- |
| `p` | Product ID | `tehjajiyfp2phy4d` |
| `v` | MCU Version | `1.0.14` |

The field definitions follow Tuya's
[MCU Standard Protocol documentation](https://developer.tuya.com/en/docs/mcu-standard-protocol/MCUSDK-wifi-base?id=Kd2bxu84567gk).
Other fields in the response, including the original Tuya pairing mode, are intentionally ignored
because they do not configure ESPHome. They remain visible in the raw product JSON printed by the
built-in Tuya component during startup.

## Recommended package

Devices in this repository use
[`packages/modules/tuya-product.yaml`](../../packages/modules/tuya-product.yaml). It creates both
sensors as diagnostic entities that are disabled by default:

```yaml
packages:
  - !include ../packages/modules/tuya-product.yaml

uart:
  id: tuya_uart
  tx_pin: TX
  rx_pin: RX
  baud_rate: 9600

tuya:
  id: tuya_mcu
  uart_id: tuya_uart
```

The module expects the Tuya UART ID to be `tuya_uart`. Its names and IDs can be customized when it is
included directly:

```yaml
packages:
  - !include
    file: ../packages/modules/tuya-product.yaml
    vars:
      tuya_product:
        uart_id: tuya_uart
        id: tuya_product_info
        pid_name: Tuya Product ID
        version_name: Tuya MCU Version
```

The module executes `tuya_ready` when ESPHome's built-in Tuya component reports that its
initialization sequence is complete. The product information is still published as soon as its
checksum-valid response is received, but it does not trigger readiness by itself. Devices can extend
the script to run actions after the initial datapoint report has been processed:

```yaml
script:
  - id: !extend tuya_ready
    then:
      - button.press: refresh_tuya_configuration
```

## Direct component use

The component can also be configured without the shared package:

```yaml
external_components:
  - source: github://yepiq/esphome-lib
    components: [tuya_product]
    refresh: 0s

uart:
  id: tuya_uart
  tx_pin: TX
  rx_pin: RX
  baud_rate: 9600

tuya:
  id: tuya_mcu
  uart_id: tuya_uart

text_sensor:
  - platform: tuya_product
    id: tuya_product_info
    uart_id: tuya_uart
    on_initialized:
      - logger.log: Tuya initialization complete
    product_id:
      name: Tuya Product ID
      disabled_by_default: true
    mcu_version:
      name: Tuya MCU Version
      disabled_by_default: true
```

Both `product_id` and `mcu_version` are optional.

## How capture works

The component attaches a receive callback to the existing UART bus. It does not consume or modify
the bytes seen by ESPHome's `tuya` component. It:

1. Watches RX traffic for a Tuya frame with header `55 AA` and command `0x01`.
2. Validates the payload length and frame checksum.
3. Parses the JSON payload and publishes the configured fields.
4. Stops processing UART data after the first checksum-valid product frame.

Separately, it attaches to the single built-in `tuya` component and exposes `on_initialized`.
ESPHome invokes this callback after the MCU startup handshake reaches `INIT_DONE`; it does not
depend on logger level, network availability, or an API client connection.

Capture is independent of the ESPHome logger level. The component does not change logger settings,
parse log messages, send commands to the MCU, or write Tuya datapoints.

Internally, it uses the byte-callback interface also used by ESPHome's UART debugger, but it does not
instantiate `uart.debug`, log UART frames, or run debugger automations. No `debug:` block is needed
under `uart:`.

The Tuya MCU must provide the product-information response during its initialization sequence.
Until that happens, the sensors remain unknown. Reboot the complete appliance when testing so both
the ESPHome module and the external Tuya MCU restart.
