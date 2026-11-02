# Heltec HRI-485X Appliances

The HRI-485X family appliance separates common configuration from model- and MCU-specific hardware.
Consumers include `../heltec-hri-485x.yaml` and select a verified profile:

```yaml
packages:
  - !include
    file: ../packages/appliances/heltec-hri-485x.yaml
    vars:
      hri485x:
        profile: hri4853
        networking:
          mode: ethernet
        rs485:
          baud_rate: 19200
          data_bits: 8
          parity: EVEN
          stop_bits: 1
```

The appliance exposes the RS485 UART as `hri485x_rs485_uart`. It does not create a Modbus hub because
RS485 is the physical transport while Modbus is an application protocol. A consuming product may add:

```yaml
modbus:
  - id: modbus_bus
    uart_id: hri485x_rs485_uart
```

## ESPHome Dashboard

```yaml
substitutions:
  name: serial-gateway
  friendly_name: Serial Gateway

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: packages/appliances/heltec-hri-485x.yaml
        vars:
          hri485x:
            profile: hri4853
            networking:
              mode: ethernet
            rs485:
              baud_rate: 19200
              parity: EVEN
```

The `hri485x` object accepts:

| Field | Default / meaning |
| --- | --- |
| `profile` | `hri4853`; only implemented profile. |
| `networking` | [Networking settings](../../modules/networking/README.md); Wi-Fi if omitted. Ethernet pin/type settings are supplied by the hardware profile. |
| `rs485.baud_rate`, `.data_bits`, `.parity`, `.stop_bits` | `9600`, `8`, `NONE`, `1`. |
| `rs485.power.name`, `.restore_mode` | `MAX3485 Power`, `RESTORE_DEFAULT_ON`. |

The UART ID and pins are fixed, not caller parameters. Use one HRI appliance per firmware. The
HRI-4853 profile supplies its own verified `sram1_as_iram` setting rather than accepting a board
replacement through `hri485x`. Cellular/LTE support is not implemented by this package.

## Family Matrix

| Model | MCU | RS485 terminal | Network/radio capability | Appliance profile |
| --- | --- | --- | --- | --- |
| HRI-4851 | ESP32-C3-FN4 | Yes | SX1262 custom LoRa | Not yet mapped |
| HRI-4851L | ESP32-C3-FN4 | Yes | SX1262 LoRaWAN | Not yet mapped |
| HRI-4852 | ESP32-D0WDQ6 | No | SX1262 plus Ethernet/LTE gateway | Not yet mapped |
| HRI-4853 | ESP32-D0WDQ6 | Yes | Ethernet/LTE | `hri4853` |

HRI-4852 is not an RS485 endpoint: Heltec documents its header as power-only and states that it
cannot communicate directly with an RS485 device. Do not treat every HRI-485X model as an RS485 UART
appliance.

## HRI-4853 ESP32 Pin Map

| Function | ESP32 resource | Configuration |
| --- | --- | --- |
| RS485 TX | GPIO33 | UART TX |
| RS485 RX | GPIO37 | UART RX |
| MAX3485 power | GPIO16 | Active-low on tested hardware; restores the last state and defaults on |
| Mode/status LED | GPIO2 | Inverted; strapping warning acknowledged |
| Network LED | GPIO3 | Inverted; serial logger disabled |
| Button | GPIO32 | Inverted input with pull-up |
| Ethernet MDC | GPIO23 | RTL8201 |
| Ethernet MDIO | GPIO18 | RTL8201 |
| Ethernet clock | GPIO17 | `CLK_OUT` |
| Ethernet PHY address | 0 | RTL8201 |

The public ESPHome device profile documents the classic-ESP32 UART, MAX3485 power, network LED, and
Ethernet mapping. The status LED and button mapping preserve the known configuration used by this
library.

The `hri4853` profile enables `esp32.framework.advanced.sram1_as_iram` because running hardware
reports that its bootloader supports SRAM1 as IRAM. It does not set `minimum_chip_revision`.

`MAX3485 Power` reports the transceiver's logical power state: `ON` drives the active-low GPIO16 low.
This polarity is verified from observed HRI-4853 hardware behavior; Heltec's public manual does not
publish the internal GPIO map or polarity. Its default `RESTORE_DEFAULT_ON` mode restores the last
state after reboot and powers the transceiver on when no saved state exists. Override it with
`hri485x.rs485.power.restore_mode` only when an application needs different startup behavior.

## Sources

- [Heltec HRI-485X family documentation](https://wiki.heltec.org/docs/devices/lorawan-application/lora-node-devices/hri-485x-rs-485/)
- [Heltec HRI-485X datasheet](https://resource.heltec.cn/download/HRI-485X/HRI-485x.pdf)
- [ESPHome Devices: Heltec HRI-485X](https://devices.esphome.io/devices/heltec-hri-485x/)

Add another profile only after its MCU target and complete GPIO map have been verified. Unsupported
profiles must fail configuration rather than inheriting the HRI-4853 map.
