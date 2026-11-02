# esphome-lib

Reusable ESPHome firmware for switches, meters, climate devices, radios and controller boards.
Use a complete [device](devices/README.md) from the ESPHome dashboard, or compose your own
application from the [hardware appliances](#hardware-appliances) and [modules](packages/modules/README.md).
These are ESPHome firmware configurations, not Home Assistant Lovelace dashboard cards.

## Start With A Device

Create an ESPHome dashboard entry and replace its YAML with a package include. For example:

```yaml
substitutions:
  name: laundry-dehumidifier
  friendly_name: Laundry Dehumidifier

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - devices/jummico-dehumidifier.yaml
```

Wi-Fi devices use `wifi_ssid` and `wifi_password` from your dashboard's `secrets.yaml` unless you
provide explicit [networking credentials](packages/modules/networking/README.md). Choose firmware
for the actual PCB/module, not only the product's retail name. Validate before installing:

```sh
esphome config laundry-dehumidifier.yaml
```

Use the dashboard's Install action to build and deploy. First-time flashing may need serial access;
[kickstart firmware](kickstart/README.md) is available for supported boards. Disconnect mains power
before attaching a serial programmer; a low-voltage programming header does not prove isolation.
Keep a recovery method available, especially when changing board targets, pins or networking.

Package parameters belong under the selected file's `vars`. This changes a relay's HA role:

```yaml
substitutions:
  name: room-light
  friendly_name: Room Light

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: devices/sonoff-basic-r4.yaml
        vars:
          entity:
            type: light
            magic_switch:
              detect_missing_pulses: true
```

For a local checkout placed beside the dashboard YAML, use the same package and vars:

```yaml
substitutions:
  name: laundry-dehumidifier
  friendly_name: Laundry Dehumidifier

packages:
  - !include esphome-lib/devices/jummico-dehumidifier.yaml
```

Local custom-component development also needs `ESPHOME_LIB_SOURCE` set to the checkout's absolute
`components` directory. Remote consumers should leave it unset. See [local validation](tests/README.md#local-components).

## Settings And Requirements

- [Device parameters and prerequisites](devices/README.md): profiles, entity roles, calibration,
  radio fans, water meters and HA dependencies.
- [Networking](packages/modules/networking/README.md): Wi-Fi, Ethernet, dual interfaces, offline
  operation, API/OTA and clocks. API encryption and OTA passwords are opt-in, not enabled by default.
- [ESPHome version requirements](packages/README.md): the highest requirement from included
  packages wins. Do not override `esphome.min_version` directly.
- [Module contracts](packages/modules/README.md): pins, relay control, energy monitoring and
  reusable behavior. An appliance includes its board; do not add a second board package.

Firmware inherits INFO logging from the base. Change it in your dashboard with `logger.level`
or `substitutions.log_level`; device packages do not choose verbosity for you. Keep any hardware
`logger.baud_rate: 0` requirement: enabling serial logs can interfere with a connected peripheral.

This library follows moving `main`, including its own external components. Pinning only a package
does not create a reproducible release snapshot. Validate dashboard configurations when updating,
and preserve installed `name`/`friendly_name`, entity IDs and explicit customizations.

## Device Catalog

The references below describe supported configuration choices, not electrical certification.
The repository's config tests do not prove every hardware revision. Hardware-specific cautions in
the linked YAML and appliance documentation take precedence. The irrigation controller is explicitly
a bench draft; products with the same name can contain different modules or datapoints.

### Relays, Sockets And Lights

Single-relay switches and sockets use the [relay entity API](devices/README.md#relay-devices).
Multi-channel products have per-channel settings; ceiling lights and the garage opener provide
their own native entities rather than that relay API.

| Device | Hardware / notes |
| --- | --- |
| [Sonoff BASIC R4](devices/sonoff-basic-r4.yaml) | ESP32-C3; Magic Switch options. |
| [Sonoff MINIR4](devices/sonoff-mini-r4.yaml) | ESP32; external wall-switch input. |
| [Tuya Mini Switch 1DC 5A](devices/tuya-mini-switch-1dc-5a.yaml) | Dry-contact relay. |
| [Tuya Mini Switch 1PM 16A](devices/tuya-mini-switch-1pm-16a.yaml) | Power monitoring. |
| [Tuya Mini Switch 1PM 20A](devices/tuya-mini-switch-1pm-20a.yaml) | Different wiring from the 16A model. |
| [Tuya Relay 1PM 30A](devices/tuya-relay-1pm-30a.yaml) | Power monitoring. |
| [Tuya Socket CBU](devices/tuya-socket-1pm-cbu.yaml) | CBU profile. |
| [Tuya Socket T34](devices/tuya-socket-1pm-t34.yaml) | T34 profile. |
| [Tuya Socket V1 CB2S](devices/tuya-socket-1pm-v1-cb2s.yaml) | V1 wiring/calibration. |
| [Tuya Socket V2 CB2S](devices/tuya-socket-1pm-v2-cb2s.yaml) | V2 wiring/calibration. |
| [Tuya Socket USB CB2S](devices/tuya-socket-1pm-usb-cb2s.yaml) | USB-equipped socket. |
| [Tuya Dry Relay 2DC 10A](devices/tuya-dry-relay-2dc-10a.yaml) | Per-channel roles; optional RF receiver. |
| [Tuya Dry Relay 4DC 10A](devices/tuya-dry-relay-4dc-10a.yaml) | Per-channel roles and channel selection. |
| [Tuya Strip 3x2 CB2S](devices/tuya-strip-3x2-cb2s.yaml) | Three paired socket groups plus USB. |
| [Tuya Strip 4PM](devices/tuya-strip-4pm.yaml) | Select `cbu` or `t1u`; [parameters](devices/README.md#tuya-strip-4pm). |
| [Tuya Ceiling Light V1 CBU](devices/tuya-ceiling-light-v1-cbu.yaml) | Fixed V1 RGB/white wiring. |
| [Tuya Ceiling Light V2 CBU](devices/tuya-ceiling-light-v2-cbu.yaml) | V2 CBU hardware profile. |
| [Tuya Ceiling Light V2 WL2H](devices/tuya-ceiling-light-v2-wl2h.yaml) | V2 Lightning hardware profile. |
| [Tuya Garage Opener](devices/tuya-garage-opener.yaml) | One closed contact; [motion and BLE cautions](devices/README.md#garage-opener). |

### Meters And Climate

| Device | Hardware / notes |
| --- | --- |
| [EARU Breaker](devices/earu-breaker.yaml) | Latching relay, BL0942 and temperature acquisition. |
| [Tuya CT Clamp 2EM 80A](devices/tuya-ct-clamp-2em-80a.yaml) | Select `cb2s` or `t1m`; [parameters](devices/README.md#tuya-ct-clamp-2em-80a). |
| [Tuya CT Clamp 3EM 63A](devices/tuya-ct-clamp-3em-63a.yaml) | Tuya MCU; configurable baud rate. |
| [Tuya CT Clamp 16EM 200A](devices/tuya-ct-clamp-16em-200a.yaml) | Phase/channel labels and visibility. |
| [Feyree Single-Phase EVSE](devices/evse-feyree-single-phase.yaml) | Separate product/protocol from the three-phase unit. |
| [Feyree Three-Phase EVSE](devices/evse-feyree-three-phase.yaml) | Realtek UART component; own datapoint meanings. |
| [Pro Breeze Dehumidifier](devices/pro-breeze-dehumidifier.yaml) | ESP-07 serial replacement; fan interface. |
| [JUMMICO Dehumidifier](devices/jummico-dehumidifier.yaml) | ESP-07 serial replacement; physical swing remains local-only. |
| [Tuya Thermostat 716](devices/tuya-thermostat-716.yaml) | Discrete BK7231N, Tuya MCU; [provisional settings](devices/README.md#tuya-thermostat-716). |
| [MELcutter](devices/melcutter.yaml) | External CN105 driver; [HA response script](devices/README.md#melcutter). |
| [MELcutter V2](devices/melcutter-v2.yaml) | Native CN105 driver; different exposed capabilities. |
| [SCHEEAIR Nova 100](devices/fan-scheeair-nova-100.yaml) | Tuya MCU fan. |
| [Tuya MT-29 Air Quality](devices/tuya-air-quality-mt29.yaml) | T1-U-HL, Tuya UART at 115200 baud. |
| [Tuya 8-in-1 Water Meter](devices/tuya-8-in-1-water-meter.yaml) | Water-quality telemetry, not a flow meter. |

### Radios And Panels

| Device | Hardware / notes |
| --- | --- |
| [RF Fan Control](devices/fan-control-433.yaml) | LilyGO or external CC1101; [fan addresses and groups](devices/README.md#rf-fan-control). |
| [Vevor 7-in-1](devices/vevor-7-in-1.yaml) | LilyGO/Heltec receiver; tune frequency to the station. |
| [wMBus](devices/wmbus.yaml) | Heltec/LilyGO receiver; add [meter profiles](devices/README.md#wmbus). |
| [BLE Advertising Proxy](devices/ble-advertising-proxy.yaml) | Select a supported ESP32 board. |
| [ESP-07 Serial Bridge](devices/esp07-serial-bridge.yaml) | Standalone Wi-Fi TCP/UART adapter; [connection settings](devices/README.md#esp-07-serial-bridge). |
| [Weather ePaper Panel](devices/weather-epaper-panel.yaml) | HA weather/forecast dependency; verify physical display wiring. |
| [Six-Zone Irrigation Controller](devices/tuya-6-zone-valve-controller.yaml) | **Bench draft.** Output polarity/load checks and final button behavior pending. |

## Hardware Appliances

Use these to supply hardware to your own application. They do not provide application-specific
Modbus registers, LVGL pages or radio protocols.

| Example device | Appliance reference |
| --- | --- |
| [KinCony KC868-A6](devices/kincony-kc868-a6.yaml) | [Original ESP32 A6](packages/appliances/kincony-kc868-a6/README.md), not A6v3. |
| [Waveshare 8DI/8RO](devices/waveshare-esp32-s3-eth-8di-8ro.yaml) | [Ethernet I/O board](packages/appliances/waveshare-esp32-s3-eth-8di-8ro/README.md). |
| [Waveshare LCD 7B](devices/waveshare-esp32-s3-touch-lcd-7b.yaml) | [Display/touch subsystem](packages/appliances/waveshare-esp32-s3-touch-lcd-7b/README.md); application owns LVGL. |
| [Heltec HRI-485X](devices/heltec-hri-485x.yaml) | [HRI family](packages/appliances/heltec-hri-485x/README.md); only implemented profiles are accepted. |
| [M5Stack PoESP32](devices/m5stack-poesp32.yaml) | Fixed Ethernet board example. |
| Vevor / wMBus / RF fans above | [Radio appliance](packages/appliances/radio-transceiver/README.md). |

## Validation And Status

The library requires ESPHome **2026.10.0** for native conditional includes; CI uses the same release.
Minimum tool version, successful configuration validation, successful firmware compilation, hardware verification
and a product's published firmware version are separate facts. An unpublished edit does not imply
a new release number. A passing configuration or build is never proof that a valve, relay or motor
will behave correctly on a particular board.

[Validation instructions](tests/README.md) cover config-only tests, local components and focused
C++ tests. Routine YAML/substitution changes need `esphome config`, not a full firmware build.
An actual installation still requires a build. This library does not replace hardware interlocks,
overcurrent protection or the manufacturer's installation requirements.

[Tuya data models](data-models/tuya/README.md) preserve cloud schemas and extracted stock settings.
A cloud datapoint model alone does not prove the presence of a serial Tuya MCU.

## License

Original library code and documentation use the [MIT License](LICENSE), including commercial reuse.
The Vevor decoder-derived device file is **GPL-2.0-or-later**, and third-party material retains its
own terms. See [licensing scope and third-party notices](THIRD_PARTY_NOTICES.md) before redistributing
sources or firmware. The Tuya model archive is vendor reference data, not a blanket MIT relicense.
