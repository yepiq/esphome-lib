# Dependency Workarounds

Read for: Dependency upgrades, custom components and upstream workarounds.

These instructions supplement [AGENTS.md](../../AGENTS.md). Paths and YAML examples are
relative to the repository root unless stated otherwise.

## Dependency Workarounds

When a defect is traced to ESPHome, LibreTiny, PlatformIO, an SDK, or another dependency, do not
stop at identifying the upstream fault. Proactively evaluate workaround layers in this order:

1. Existing configuration or extension hooks
2. Application-level overrides
3. Linker wrapping, symbol aliases, and build flags
4. Small external components
5. Temporary dependency patches or forks

Prefer the narrowest reversible solution that keeps upstream dependencies unmodified. Verify the
mechanism against the relevant source and actual toolchain before recommending or implementing it.
Document the upstream issue, any version-specific assumptions, and how to remove the workaround
after an official fix becomes available.

### Pending: Remove The Beken UART Read Guard

Monitor [LibreTiny issue #154](https://github.com/libretiny-eu/libretiny/issues/154) and
[PR #432](https://github.com/libretiny-eu/libretiny/pull/432). The shared Beken template loads
`bk72xx_uart_guard` to protect `SerialClass::read()` with saved/restored IRQ and FIQ masks.
It is required by the interrupt-unsafe receive ring in LibreTiny 1.13.0. Do not copy the ARMv5
mask implementation into the Realtek or Lightning templates.

Once ESPHome's selected LibreTiny release includes the upstream fix, verify the actual Serial
read and interrupt handling in that release, then remove the local read wrapper and linker flag
from the shared Beken layer. Validate and compile BK7231N and BK7238 consumers and check that
serial reads remain interrupt-safe.

### Pending: Remove The Beken OTA Packaging Workaround

The shared Beken template loads `bk72xx_ota_packaging` to select PyCryptodome in LibreTiny's
build environment. ltchiptool 4.15.0's PyAES backend adds a second AES padding layer, which
can trigger a BK7231N bootloader verification defect at a 4096-byte compressed-input boundary.
Track [ltchiptool PR #104](https://github.com/libretiny-eu/ltchiptool/pull/104) through merge
and the first [ltchiptool release](https://github.com/libretiny-eu/ltchiptool/releases) containing
the fix. Before removal, confirm the supported LibreTiny toolchain requires a fixed ltchiptool
version and check the version actually installed in its Python environment. Verify PyAES directly
and validate the 4096-byte OTA boundary in a clean ARM-host Beken build. Then remove the component,
its base-board registrations, validation references and this pending note. See the component README.

### Pending: Remove The Realtek Reboot Workaround

During ESPHome upgrades, check the LibreTiny version actually selected for RTL8720C builds.
[LibreTiny PR #397](https://github.com/libretiny-eu/libretiny/pull/397), released in 1.14.0,
changes `lt_reboot()` to call `sys_reset()`.

Once the library's supported ESPHome baseline selects LibreTiny 1.14.0 or later with that fix,
remove `-Wl,--wrap=lt_reboot` and `-Wl,--defsym=__wrap_lt_reboot=sys_reset` from
`packages/boards/templates/base-board-libretiny-realtek.yaml`. Run configuration validation and
compile an affected WBR3/RTL8720C target, such as `devices/fan-scheeair-nova-100.yaml`, confirming
the resolved framework version and absence of both flags. Remove this pending note when complete.
