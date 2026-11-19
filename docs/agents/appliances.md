# Appliance Packages

Read for: Appliance profiles, fixed wiring and public hardware APIs.

These instructions supplement [AGENTS.md](../../AGENTS.md). Paths and YAML examples are
relative to the repository root unless stated otherwise.

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
