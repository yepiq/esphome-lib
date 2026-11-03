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

CT16 retains LibreTiny's default receive-ring capacity of 256 bytes. `uart.rx_buffer_size`
does not resize the ring in the tested LibreTiny path; the framework option controlling its
capacity is `LT_SERIAL_BUFFER_SIZE`.

## Upstream removal

Monitor [LibreTiny issue #154](https://github.com/libretiny-eu/libretiny/issues/154) and
[PR #432](https://github.com/libretiny-eu/libretiny/pull/432). Once the LibreTiny release selected
by ESPHome contains the fix, verify its interrupt-safe Serial implementation and remove the local
read wrapper and `--wrap=_ZN11SerialClass4readEv` flag. Revalidate and compile BK7231N and BK7238
consumers, checking their generated calls. See the matching pending-removal note in `AGENTS.md`.

## Validation

Run `python components/bk72xx_uart_guard/tests/test_uart_guard.py` for deterministic host tests
of the real read wrapper with interrupt and UART doubles. These exercise the lost-update
control, saved mask states, both ports, FIFO order and full/empty/wraparound handling. ARM
instruction semantics and linker interception additionally require the affected firmware
builds and disassembly checks.
