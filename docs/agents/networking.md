# Networking Framework

Read for: Networking, time, API, OTA, mDNS and interface selection.

These instructions supplement [AGENTS.md](../../AGENTS.md). Paths and YAML examples are
relative to the repository root unless stated otherwise.

## Networking Framework

`packages/modules/networking.yaml` is included by `base-board.yaml`. Select one interface (or no
network) with `networking.mode`:

```yaml
vars:
  networking:
    mode: wifi # wifi | ethernet | none
```

Responsibilities:

- select interfaces through `networking.interfaces` (an ordered list of `wifi`/`ethernet`, or `[]`)
  or `networking.mode`; specifying both is invalid
- expose API, OTA, and mDNS defaults only with a network, with individual `enabled` controls
- own HA time, connectivity status and uptime's clock-dependent form; offline/no-clock uptime is
  elapsed seconds, with no fabricated clock or implicit network prerequisite
- use `pin.yaml` for Ethernet pin-number fields
- disable API and Wi-Fi connection-loss reboots by default with `reboot_timeout: 0s`

Ethernet type selects the physical schema. RMII PHYs use `mdc_pin`, `mdio_pin`, `clk_pin`,
`clk_mode`, and `phy_addr`; SPI controllers such as W5500 use `clk_pin`, `mosi_pin`, `miso_pin`,
`cs_pin`, `interrupt_pin`, and `reset_pin`. Keep those implementations separate because ESPHome
rejects fields from the wrong Ethernet schema.

Device-specific networking overrides should travel through the board package include so the base-board
layer and nested networking package see the same package context:

```yaml
packages:
  - !include
    file: ../packages/boards/espressif/m5stack-core-esp32.yaml
    vars:
      networking:
        mode: ethernet
        ethernet:
          type: IP101
          mdc_pin: GPIO23
          mdio_pin: GPIO18
          clk_pin: GPIO0
          power_pin: GPIO5
```

The two interface selectors use deferred includes. Keep them lazy: preloading all variants would
resolve Wi-Fi secrets even for Ethernet-only/offline devices. `networking/settings.yaml` is the
shared normalization used by the assembler and appliance-owned HA/RTC hooks; do not
duplicate those decisions in wrappers. Forward complete networking objects, retaining fixed
appliance Ethernet wiring. Clock synchronization and API LED hooks must not recreate disabled
services. Device-level HA actions and explicit clock references remain consumer prerequisites;
unsupported offline combinations must fail, not silently become no-ops.

Dual-interface mode uses ESPHome's native `network.priority`, requires ESP32/2026.8.0, and keeps
per-interface IP/MAC diagnostics distinct. Single-interface IDs, names and defaults are preserved.
Explicit Ethernet `enable_on_boot` also requires 2026.8.0; leave that schema key absent by default
so existing single-interface packages retain their minimum version.
Do not implement a custom failover loop. Test both priority orders, offline platforms, disabled
services, explicit RTC clocks and rejected dependencies. Consumer configuration and accepted
fields are documented in `packages/modules/networking/README.md`.
