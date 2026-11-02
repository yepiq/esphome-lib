# Radio Transceiver

This appliance supplies a board, SPI bus, transceiver and optional integrated OLED. Your application
supplies protocol decoding, entities and automations. Include it once per firmware: infrastructure
IDs are fixed. Complete [Vevor, wMBus and RF fan devices](../../../devices/README.md) already include it.

## Hardware And Drivers

| `radio.profile` | Hardware | Supported `radio.driver` |
| --- | --- | --- |
| `heltec` (default) | Heltec WiFi LoRa 32 V2 / SX127x / OLED | `sx127x`, `wmbus`, `raw` RX only |
| `lilygo` | LilyGO TTGO LoRa32 V2.1 / SX127x / OLED | `sx127x`, `wmbus`, `raw` TX/RX |
| `esp32dev_cc1101` | ESP32 DevKit with external CC1101 | `raw` TX/RX only; no integrated OLED |

Heltec's DIO2 is input-only GPIO34. For raw reception set `raw.transmitter.enabled: false` and
`raw.receiver.enabled: true`; raw transmission intentionally fails configuration. Unsupported
profiles/driver combinations fail instead of silently selecting a different board.

```yaml
substitutions:
  name: radio-receiver
  friendly_name: Radio Receiver

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: packages/appliances/radio-transceiver.yaml
        vars:
          radio:
            profile: lilygo
            driver: raw
            frequency: 433.92MHz
            display:
              enabled: false
            raw:
              transmitter:
                enabled: false
              receiver:
                enabled: true

remote_receiver:
  - id: !extend radio_receiver
    dump: rc_switch
```

## Parameters

Pass a `radio` object under the include's `vars`:

| Field | Default / meaning |
| --- | --- |
| `profile` | `heltec`; physical wiring selection above. |
| `driver` | `sx127x`; packet radio, wMBus or raw pulse I/O. |
| `frequency` | `433.92MHz`; match hardware band and transmitter. |
| `display.enabled` | true; ignored on the CC1101 profile without a display. |
| `raw.transmitter.enabled` | true, for the raw driver. |
| `raw.receiver.enabled` | false, for the raw driver. |
| `raw.transmitter.non_blocking` | false. |
| `raw.transmitter.after_transmit` | `standby` on SX127x, `idle` on CC1101; `rx` returns to reception. |
| `raw.transmitter.on_complete` | `[]`; additional actions after the radio's completion action. |

`raw.transceiver` accepts driver-specific options:

| Hardware | Fields and defaults |
| --- | --- |
| SX127x | `modulation: OOK`, `bandwidth: 125_0kHz`, `bitsync: false`, `packet_mode: false`, `rx_start: false`, `pa_pin: BOOST`, `pa_power: 17`. |
| CC1101 | `modulation_type: ASK/OOK`, `packet_mode: false`, `filter_bandwidth: 203kHz`, `symbol_rate: 5000`, `output_power: 10`. |

Use native `!extend` for additional receiver/packet-driver options. `raw.receiver` accepts only
`enabled`; it does not forward arbitrary ESPHome receiver fields. Set `esp32_advanced` and
`networking` as sibling vars, not inside `radio`. Applications using wMBus must declare its external
components and meter profiles, as demonstrated by the complete wMBus device.

## Wiring And Ownership

| Signal | Heltec | LilyGO | ESP32 + CC1101 |
| --- | --- | --- | --- |
| SPI CLK / MOSI / MISO | GPIO5 / 27 / 19 | GPIO5 / 27 / 19 | GPIO18 / 23 / 19 |
| Chip select | GPIO18 | GPIO18 | GPIO5 |
| Reset | GPIO14 | GPIO23 | Not used |
| Raw TX / RX | Not supported / GPIO34 | GPIO32 / GPIO32 | GPIO26 / GPIO25 |
| OLED SDA / SCL | GPIO4 / GPIO15 | GPIO21 / GPIO22 | Not present |

Use an appropriate 3.3 V supply and common ground for the external radio. Pin mappings do not
establish antenna suitability, legal frequency/power settings or electrical isolation.

Stable IDs are `radio_spi`, `radio_transceiver`, and, when enabled, `radio_transmitter`,
`radio_receiver`, `radio_i2c`, `radio_oled_font`, `radio_display` and `radio_status_led`.
Raw-radio applications may call scripts `radio_enter_tx`, `radio_enter_rx`, `radio_enter_idle`
and `radio_after_transmit`. The transmitter switches mode around transmission automatically.
The appliance owns those components and fixed wiring; do not create a second board or SPI bus
for the same hardware.
