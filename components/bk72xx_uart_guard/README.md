# Beken UART guard

The shared Beken board template registers this component. It activates only when the resolved
ESPHome configuration contains a `uart:` bus, including buses supplied by packages. Without a
UART bus, code generation adds no wrapper flag and ESPHome's source filter excludes all of this
component's C++ sources and headers. The Python registration remains in the shared template so
consumers do not need to enable the guard individually.

The guard wraps LibreTiny's nonblocking `SerialClass::read()` for all hardware serial ports.
It saves the ARM968 IRQ/FIQ masks, disables both while reading one byte, then restores both masks
together. It never holds the mask while waiting for input or parsing a frame. It does not change
buffer capacity, restart UARTs, flush received data, or create an entity.

This addresses the shared `_numElems` lost-update race in LibreTiny 1.13.0 / ArduinoCore-API
2022.08.24. Beken's `beken-72xx` build family selects ARM968E-S; the ARMv5 implementation must not
be copied into Realtek or Lightning builds. The compiler rejects an incompatible architecture.
The linker symbol and Serial vtable interception must be checked again after framework upgrades.

## Optional overflow counter

The CT16 device enables this temporary diagnostic. Other Beken devices inherit only the guard.
Inside an existing Beken device with a receive UART, add:

```yaml
sensor:
  - platform: bk72xx_uart_guard
    name: UART RX Overflows
    id: uart_rx_overflows
    uart_id: tuya_uart
```

Each event is one incoming byte discarded because the **software receive ring is full**. A burst
that drops 20 bytes increments the counter by 20. This does not count hardware FIFO overruns,
framing/parity errors, CRC failures, or stale sensors. Zero here therefore does not rule out all
UART faults. The native API sensor has diagnostic category and `total_increasing` state class.

The optional hook observes `uart_read_byte()` immediately before LibreTiny's receive callback
calls `store_char()`. SDK ports 0/1 correspond to `Serial1`/`Serial2`. Counting starts when the UART
starts, before the sensor initializes, so startup drops are included. The ISR only increments a
RAM counter. A normal polling update (default 1 second) publishes the total and queues changes in
ESPHome preferences. No logs, sensor publishing, allocations, or flash writes occur in the ISR.

A stable, per-hardware-port preference key preserves the cumulative total across normal reboots,
OTA reflashes, and sensor renames. Shutdown samples the final count and syncs preferences. Normal
ESPHome flash batching remains in effect: sudden power loss can lose recent unsaved increments.
Erasing preferences or a full flash erase resets the counter. One monitor per hardware UART is
supported; the storage key must remain unchanged while retained counts are wanted.

The sensor does not resize the ring. CT16 keeps the actual LibreTiny default of 256 bytes during
this investigation. `uart.rx_buffer_size` does not resize the ring in the tested LibreTiny path;
if overflow evidence later justifies resizing, the framework option is `LT_SERIAL_BUFFER_SIZE`.
The sensor's config dump reports that actual compile-time capacity.

## Upstream removal

Monitor [LibreTiny issue #154](https://github.com/libretiny-eu/libretiny/issues/154) and
[PR #432](https://github.com/libretiny-eu/libretiny/pull/432). Once the LibreTiny release selected
by ESPHome contains the fix, verify its interrupt-safe Serial implementation and remove the local
read wrapper and `--wrap=_ZN11SerialClass4readEv` flag. Revalidate and compile BK7231N and BK7238
consumers, checking their generated calls. The optional overflow sensor is independent diagnostic
instrumentation; retain it until that investigation is complete. See the matching pending-removal
note in `AGENTS.md`.

## Validation

Run `python components/bk72xx_uart_guard/tests/test_uart_guard.py` for deterministic host tests
of the real wrappers and sensor with interrupt, UART and preference doubles. These exercise the
lost-update control, saved mask states, FIFO order, overflow/empty/other-port handling, startup
counts, batching, and restoration after reboot/reflash. ARM instruction semantics and SDK hook
placement additionally require the affected firmware builds and disassembly checks.
