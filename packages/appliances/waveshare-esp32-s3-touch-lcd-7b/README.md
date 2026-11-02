# Waveshare ESP32-S3-Touch-LCD-7B

This appliance provides the display subsystem of the Waveshare
ESP32-S3-Touch-LCD-7B (touch version, SKU 31726):

- ESP32-S3-WROOM-1-N16R8
- 16 MB flash and 8 MB octal PSRAM
- 1024 x 600 RGB565 display
- GT911 capacitive touchscreen at I2C address `0x5D`
- CH32V003 I/O extension at I2C address `0x24`
- controllable backlight with brightness and full on/off support

The board's I/O extension is not the CH422G used by some other Waveshare LCD
boards. ESPHome supports it natively through `waveshare_io_ch32v003`.

## Local Usage

```yaml
packages:
  - !include
    file: ../packages/appliances/waveshare-esp32-s3-touch-lcd-7b.yaml
    vars:
      waveshare_lcd7b:
        backlight:
          id: display_backlight
          name: Display Backlight

lvgl:
  rotation: 0
  buffer_size: 25%
```

## Remote Package Usage

```yaml
substitutions:
  name: display-panel
  friendly_name: Display Panel

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - path: packages/appliances/waveshare-esp32-s3-touch-lcd-7b.yaml
        vars:
          waveshare_lcd7b:
            backlight:
              id: display_backlight
              name: Display Backlight

light:
  - id: !extend display_backlight
    restore_mode: RESTORE_DEFAULT_ON

lvgl:
  rotation: 0
  buffer_size: 25%
```

Pass both the backlight `id` and `name` when an application extends it. Replacing
only the id leaves the appliance's default entity name, `Backlight`.

The display defaults to `update_interval: never` and
`auto_clear_enabled: false`, as required by LVGL. Applications using ESPHome's
display drawing engine instead may override both values under
`waveshare_lcd7b.display`.

The appliance owns the display and touch hardware, while the application owns
the `lvgl` block, including rotation, buffer sizing, pages, widgets, and idle
behavior. With one display and one touchscreen, LVGL selects both automatically.

Applications may target these stable default ids:

- `waveshare_lcd7b_display`
- `waveshare_lcd7b_touchscreen`
- `waveshare_lcd7b_backlight`
- `waveshare_lcd7b_backlight_output`
- `waveshare_lcd7b_backlight_power`
- `waveshare_lcd7b_i2c`
- `waveshare_lcd7b_io`

The display, touchscreen, and backlight entity ids may be replaced through the
corresponding `waveshare_lcd7b` objects. Display drawing applications can also
set `display.update_interval` and `display.auto_clear_enabled`.

## Parameters

The `waveshare_lcd7b` object accepts only the settings below; physical pins/timings remain fixed.

| Field | Default |
| --- | --- |
| `display.id` | `waveshare_lcd7b_display` |
| `display.update_interval` | `never` |
| `display.auto_clear_enabled` | `false` |
| `touchscreen.id` | `waveshare_lcd7b_touchscreen` |
| `backlight.id` | `waveshare_lcd7b_backlight` |
| `backlight.name` | `Backlight` |
| `backlight.restore_mode` | `RESTORE_DEFAULT_ON` |
| `backlight.transition_length` | `250ms` |
| `networking` | Shared [networking settings](../../modules/networking/README.md); Wi-Fi by default. |

## GT911 Initialization Workaround

I2C deliberately runs at **50 kHz with `scan: false`**. At 400 kHz, the panel has exhibited
intermittent GT911 startup failures, an address change from `0x5D` to `0x14`, and `Calibration error`.
The lower bus rate is a temporary mitigation for [ESPHome issue #15019](https://github.com/esphome/issues/issues/15019).
Do not add a second I2C bus or a 400 kHz override when consuming this appliance.

Revisit the rate only after an upstream GT911 fix is available and repeated cold boots/restarts
on this board confirm reliable initialization at 400 kHz. Keep scanning disabled. The YAML retains
the same workaround comment next to the setting so the reason is visible during configuration.

## Fixed Wiring

| Function | Connection |
| --- | --- |
| I2C SDA / SCL | GPIO8 / GPIO9 |
| Touch interrupt | GPIO4 |
| Display DE / PCLK | GPIO5 / GPIO7 |
| Display VSYNC / HSYNC | GPIO3 / GPIO46 |
| Red data | GPIO1, GPIO2, GPIO42, GPIO41, GPIO40 |
| Green data | GPIO39, GPIO0, GPIO45, GPIO48, GPIO47, GPIO21 |
| Blue data | GPIO14, GPIO38, GPIO18, GPIO17, GPIO10 |
| Touch reset | Extension pin 1 |
| Backlight enable | Extension pin 2 |
| Display reset | Extension pin 3 |

The RGB timing follows Waveshare's current 7B driver: 24 MHz pixel clock,
HSYNC 162/152/48, and VSYNC 45/13/3 for pulse/back/front porch.

Extension pin 6 is intentionally left unassigned. Waveshare's current driver
sets the RGB display enable GPIO to `-1` and does not drive that extension pin.

This appliance intentionally owns only the display subsystem. Other onboard
interfaces remain available to consuming firmware. GPIO6 is a general exposed
pin on this board; it is not modeled as an onboard buzzer.
