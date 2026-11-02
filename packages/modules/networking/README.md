# Networking

Board packages include networking automatically. Pass `networking:` through the board's `vars`,
or through the appliance's own networking object (`hri485x.networking`,
`waveshare_8di8ro.networking`, `waveshare_lcd7b.networking`, or `kincony_kc868_a6.networking`).
Do not include the networking module a second time. It supports one network stack per firmware,
with one Wi-Fi interface and/or one Ethernet interface.

## ESPHome Dashboard

This example uses the Waveshare board's built-in W5500 and adds Wi-Fi as a second interface:

```yaml
substitutions:
  name: utility-controller
  friendly_name: Utility Controller

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: devices/waveshare-esp32-s3-eth-8di-8ro.yaml
        vars:
          waveshare_8di8ro:
            networking:
              interfaces: [ethernet, wifi]
              wifi:
                ssid: !secret wifi_ssid
                password: !secret wifi_password
```

The same `vars` object works with a local `!include`. Each appliance retains its normal default:
Waveshare 8DI/8RO uses Ethernet; the other listed appliances use Wi-Fi. Omit networking settings
to keep that default. Fixed Ethernet wiring remains owned by the appliance.

Networking contributes its feature requirements to the shared
[version resolver](../../README.md). Other packages can demand a higher version independently;
do not override `esphome.min_version` to combine them.

## Interfaces

Choose **one** selector:

| Setting | Meaning |
| --- | --- |
| `mode: wifi` | Wi-Fi only; generic board default. |
| `mode: ethernet` | Ethernet only. |
| `mode: none` | No network. |
| `interfaces: [wifi]` or `[ethernet]` | Equivalent single-interface selection. |
| `interfaces: [ethernet, wifi]` | Both, preferring Ethernet. |
| `interfaces: [wifi, ethernet]` | Both, preferring Wi-Fi. |
| `interfaces: []` | No network. |

Duplicate/unknown interfaces, a non-list `interfaces` value, and combining `mode` with `interfaces`
are configuration errors. Interface options do not enable an interface by themselves.

Dual-interface operation requires **ESP32** and uses native support introduced in ESPHome 2026.8.0
(the library now requires 2026.10.0). The list becomes ESPHome's
native `network.priority`. The first connected interface in that order carries outgoing traffic, with
native failover/failback and DNS selection. Each interface has its own address; this is not bridging
or link aggregation. See [ESPHome's multi-interface documentation](https://esphome.io/components/network/#multi-interface-support).

Both interfaces start enabled. Set `wifi.enable_on_boot: false` or `ethernet.enable_on_boot: false`
to keep one off until your automation calls `wifi.enable` or `ethernet.enable`. A disabled interface
cannot provide automatic failover. Explicit `ethernet.enable_on_boot` also requires ESPHome 2026.8.0
when using Ethernet alone; omitting it keeps the existing minimum version. Running both stacks
costs additional memory. The library's configurations are schema-tested; validate link changes
and API reconnection on your actual board
before relying on failover.

Single-interface diagnostic IDs and names are unchanged. With both interfaces configured, IP/MAC
diagnostics use separate `mcu_wifi_ip_address`, `mcu_wifi_mac_address`, `mcu_ethernet_ip_address`,
and `mcu_ethernet_mac_address` IDs, with WiFi/Ethernet-prefixed names.

Wi-Fi configurations also provide a `WiFi Roam` configuration button (`mcu_wifi_roam`), disabled by
default in Home Assistant. Pressing it requests an immediate roaming scan through `wifi.roam`.
It is included in both Wi-Fi-only and dual-interface configurations.

## Services And Time

| Option | Default / accepted values |
| --- | --- |
| `api.enabled` | `true` with a network, otherwise `false`. |
| `api.reboot_timeout` | `0s`; other native API options are forwarded. Default API ID: `hapi`. |
| `ota.enabled` | `true` with a network, otherwise `false`. Other options apply to ESPHome OTA. |
| `mdns.enabled` | `true` with a network, otherwise `false`. Other native mDNS options are forwarded; use `enabled`, not `disabled`, here. |
| `time.source` | `homeassistant` when API is enabled, otherwise `none`; also accepts `external`. |
| `time.id` | `ha_time` for Home Assistant time; required for `external`. |

`enabled` accepts booleans. Explicitly enabling a network service without an interface is an error.
Home Assistant time requires API. `time.source: external` creates no clock: you must provide a
native ESPHome time component with the specified ID, such as an RTC or SNTP clock. SNTP still
requires a network. The library does not create a placeholder clock or fabricate valid time.

API encryption and OTA authentication remain opt-in. Configure native API encryption and OTA
password settings either in these objects or in your dashboard's native component blocks.

`mcu_uptime` retains its existing timestamp form when a clock is selected. Without a selected clock
it reports elapsed seconds (`duration`). The connectivity status entity is omitted when offline.
On RTC-equipped appliances, HA-to-RTC write hooks exist only when Home Assistant time is selected;
the physical RTC remains available regardless of networking mode.

## Offline Devices

An offline board with local GPIO controls needs no Wi-Fi secrets, API, OTA, mDNS, or HA clock:

```yaml
packages:
  - !include
    file: ../packages/boards/espressif/esp32dev.yaml
    vars:
      networking:
        interfaces: []
```

This does **not** convert every complete device into an offline product. A detached relay needs HA
actions, and a device may explicitly reference `ha_time` or an HA sensor. Those requirements still
fail validation until you remove that feature or supply its real prerequisite. For Tuya, its
`time_id` is optional upstream, but a device which sets it still needs that clock. Override the
device's `tuya.time_id` to an actual RTC ID, provide a clock named `ha_time`, or remove the optional
reference only if the device does not need MCU time synchronization.

For a Waveshare controller using its RTC offline:

```yaml
vars:
  waveshare_8di8ro:
    networking:
      interfaces: []
      time:
        source: external
        id: waveshare_8di8ro_rtc
```

The RTC must already contain valid time. For KC868-A6, the default RTC ID is `rtc_time`.
**Offline firmware has no network OTA path.** Plan physical/serial access before deploying it.

## Interface Options

Under `networking.wifi`:

| Field | Default |
| --- | --- |
| `ssid` | `!secret wifi_ssid`, loaded only when omitted and Wi-Fi is selected. |
| `password` | `!secret wifi_password`, loaded only when omitted and Wi-Fi is selected; `''` means an open network. |
| `reboot_timeout` | `0s`. |
| `enable_on_boot` | `true`. |

Under `networking.ethernet`, generic boards accept the fields below. Appliance packages supply their
fixed wiring. Select a board/PHY combination actually supported by ESPHome and your hardware.

| Field | Default / scope |
| --- | --- |
| `type` | `LAN8720`; `W5500`, `DM9051`, `ENC28J60` select the SPI schema. Other types use RMII. |
| `enable_on_boot` | `true`, both schemas. |
| `mdc_pin`, `mdio_pin` | `GPIO23`, `GPIO18`; RMII. |
| `clk_pin`, `clk_mode`, `phy_addr` | RMII: `GPIO0`, `CLK_EXT_IN`, `1`. |
| `power_pin` | Optional RMII PHY power pin; absent by default. |
| `clk_pin`, `mosi_pin`, `miso_pin`, `cs_pin`, `interrupt_pin`, `reset_pin` | Supply all for SPI Ethernet. |
| `clock_speed`, `interface` | SPI: `26.67MHz`, `spi2`. |
| `<pin-stem>_strapping` | Optional ESP32 strapping-warning flag; `clk_strapping` defaults to `true` for RMII, all others to `false`. |

Other native interface options, such as `manual_ip`, `use_address`, Wi-Fi power saving, or connection
automations, belong in the dashboard's top-level `wifi:` or `ethernet:` block. Do not add unlisted
fields to these library interface objects and expect them to be forwarded. See the native
[Wi-Fi](https://esphome.io/components/wifi/) and [Ethernet](https://esphome.io/components/ethernet/)
references for those overrides. Unknown top-level `networking` and `networking.time` keys are rejected.
