# RTL8720C UART

`rtl8720c_uart` provides an ESPHome UART bus backed directly by the Realtek AMB-Z2 `serial_api`.
It is intended for RTL8720C modules whose valid UART0 pin mapping is not recognized by the stock
ESPHome LibreTiny UART backend.

The component currently supports UART0 only. It has been hardware-tested on WBR3 using PA14 for TX
and PA13 for RX.

```yaml
external_components:
  - source: github://yepiq/esphome-lib
    components:
      - rtl8720c_uart

rtl8720c_uart:
  id: hardware_uart
  tx_pin: PA14
  rx_pin: PA13
  baud_rate: 9600
```

The generated component implements ESPHome's `UARTComponent` interface, so consumers can select it
with their normal `uart_id` option.

This is an application-level workaround for the UART pin-selection behavior tracked in
[ESPHome issue #13596](https://github.com/esphome/esphome/issues/13596). Its low-level initialization
follows the hardware-UART approach from
[LibreTiny pull request #359](https://github.com/libretiny-eu/libretiny/pull/359). Remove the
component once the same pin mapping is supported by released ESPHome and LibreTiny versions.
