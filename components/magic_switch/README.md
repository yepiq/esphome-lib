# Magic Switch

Interrupt-driven detector for the Sonoff BASICR4 `GPIO5` zero-cross/magic-switch signal.

The signal normally contains a short high pulse on each mains half-cycle. A wall-switch transition
disturbs that stream. The component learns the normal pulse width and zero-cross period during the
startup mask, then uses both pulse width and mains phase to classify later disturbances.

Unlike a single-threshold detector, it:

- initializes from the actual GPIO level, so booting while the pin is high cannot create a stale pulse;
- enables the GPIO pull-up by default;
- rejects pulses below `min_pulse` unless they are off the learned zero-cross phase;
- bounds accepted pulses with `max_pulse`;
- waits for normal zero-cross pulses to return before publishing one event;
- collapses contact bounce with `debounce`;
- provides `magic_switch.mask` so relay changes cannot feed back as wall-switch events;
- logs calibration, accepted pulse lengths, filtered-event counters, and unusual below-threshold
  pulses that can reveal a missed quick wall-switch movement.
- can opt into an IRAM-safe ESP-IDF GPIO interrupt service so flash writes cannot defer pulse edges.

```yaml
external_components:
  - source: github://yepiq/esphome-lib
    components: [magic_switch]

magic_switch:
  id: wall_switch
  pin: GPIO5
  iram_safe_interrupt: true
  min_pulse: 1ms
  max_pulse: 120ms
  detect_missing_pulses: false
  adaptive_min_pulse: 750us
  adaptive_margin: 200us
  phase_tolerance: 1ms
  recovery_pulses: 2
  recovery_timeout: 150ms
  startup_mask: 2s
  debounce: 250ms
  on_switch:
    - logger.log:
        format: "Magic-switch pulse: %u us"
        args: [pulse_us]

switch:
  - platform: gpio
    id: relay
    pin: GPIO4
    on_turn_on:
      - magic_switch.mask:
          id: wall_switch
          duration: 500ms
    on_turn_off:
      - magic_switch.mask:
          id: wall_switch
          duration: 500ms
```

`min_pulse` remains the principal stability control. The adaptive threshold is only used for an
off-phase pulse and never goes below `adaptive_min_pulse`. Lowering either value increases
sensitivity and the chance of classifying mains noise as a switch event.

Set `detect_missing_pulses: true` to also treat one or two absent zero-cross pulses as a candidate.
The gap must be phase-aligned at two or three times the learned mains period, outside all masks, and
followed by the same configured recovery pulses as a wide-pulse candidate. This is opt-in because a
real mains disturbance and a switch transition can produce the same observable waveform.

The relay mask is deliberately separate from `debounce`: call `magic_switch.mask` on every local or
remote relay state change. `mask` extends an existing mask and never shortens the startup interval.

`iram_safe_interrupt` is an ESP32 ESP-IDF-only workaround for ESPHome installing its shared GPIO
interrupt service without `ESP_INTR_FLAG_IRAM`. When enabled, the component wraps
`gpio_install_isr_service` at link time and adds the IRAM flag. This affects every GPIO interrupt
handler in the firmware, so enable it only after verifying that all of those handlers and their
complete call paths are IRAM-safe. The BASICR4 profile has been checked with the final linked ELF.
Because the GPIO interrupt service is global, enabling the option on any instance enables it for the
whole firmware.

No algorithm observing only `GPIO5` can perfectly distinguish a real wall-switch transition from a
mains disturbance with the same waveform. The upper bound and recovery check reduce that risk, but
hardware logs remain the final basis for tuning.

## Design references

- [Tasmota `xdrv_71_magic_switch`](https://github.com/arendst/Tasmota/blob/development/tasmota/tasmota_xdrv_driver/xdrv_71_magic_switch.ino)
  supplies the pull-up, paired-edge reset, single pending pulse, 4 ms default threshold, and 250 ms
  masking-window precedents.
- [Tasmota issue #22535](https://github.com/arendst/Tasmota/issues/22535) and
  [fix #22539](https://github.com/arendst/Tasmota/pull/22539) demonstrate a 4566 us false pulse from
  relay switching and apply the mask to every relay power change.
- [`ssieb/esphome_components` PR #97](https://github.com/ssieb/esphome_components/pull/97) adds
  captured-level edge pairing to the original ESPHome component. This component retains that fix and
  also resets each rise explicitly.
- [YoMan12's BASICR4 firmware](https://github.com/YoMan12/Sonoff_BASICR4_magic-switch) supplies the
  configurable lower/upper pulse bounds and pulse-duration diagnostics precedents.

Sonoff documents the feature behavior but does not publish the BASICR4 factory detection algorithm.
The implementation here is therefore an independent detector, not a reproduction of proprietary
firmware.
