# LN882H PWM

`ln882h_pwm` provides ESPHome float outputs using the LN882H SDK's advanced timers. It is a
temporary application-level workaround for the missing `analogWrite()` implementation in
LibreTiny 1.13.0, tracked in [LibreTiny issue #369](https://github.com/libretiny-eu/libretiny/issues/369).
ESPHome's standard `libretiny_pwm` output reaches that missing function; configuration settings
alone cannot provide it.

```yaml
external_components:
  - source: github://yepiq/esphome-lib
    components: [ln882h_pwm]

output:
  - platform: ln882h_pwm
    id: red_pwm
    pin: PA07
    timer: 0
    frequency: 4000 Hz
```

Each output reserves one complete advanced timer, using its A channel. `timer` is required,
ranges from 0 to 5, and must be unique among these outputs. The normal ESPHome internal GPIO
schema validates and reserves `pin`; pin inversion and standard float-output power scaling
are supported. Frequency is fixed at setup, defaults to 4 kHz, and accepts 100 Hz–20 kHz.
Do not share these timers with another driver.

The driver selects the smallest prescaler that fits the hardware's 16-bit period and 6-bit
prescaler. It keeps zero/full duty as static GPIO levels and uses the SDK's positive-duty timer
polarity for intermediate values. This follows the endpoint and AFIO handling in
[`ln_drv_pwm.c`](https://github.com/libretiny-eu/framework-lightning-ln882h/blob/master/project/mcu_peripheral_driver_demo/PWM/bsp/ln_drv_pwm.c).
The HAL headers, timer register limits, GPIO encoding, and SDK build inclusion were checked
against the locally installed LibreTiny 1.13.0 toolchain packages.

The [existing community component](https://github.com/Nouxii/esphome-ln882-pwm) was reviewed.
This implementation additionally uses ESPHome's pin validation, rejects duplicate timers,
handles static duty endpoints, and retains timer resolution below 10 kHz. It leaves LibreTiny
and the SDK unmodified; supplying a global `analogWrite` override would instead affect all
consumers of that Arduino API.

Validation for the initial WL2H integration is limited to `esphome config` on ESPHome 2026.8.2,
at the owner's request. Compilation and physical PWM verification remain owner-run steps.
Once released LibreTiny versions support LN882H `analogWrite`, migrate the device outputs to
`libretiny_pwm`, verify the PWM frequency/polarity/endpoints, and remove this component and its
`external_components` declaration.
