# AGENTS.md - esphome-lib

## What This Repository Is

`esphome-lib` is a reusable ESPHome package library. It provides:

- board packages that describe MCU families and physical board targets
- base-board packages that add common ESPHome services and diagnostics
- appliance packages that assemble a board and its integrated peripherals
- networking packages for Wi-Fi, Ethernet, API, OTA, and mDNS
- functional modules for relays, lights, switches, energy monitors, and integrations
- concrete `devices/*.yaml` files that compose those packages into real devices
- minimal `kickstart/*.yaml` firmware for first UART flashes of supported boards

This repository is actively used. Treat it like production infrastructure: make small, deliberate,
validated changes, and preserve intentional device values.

## Read The Relevant Guidance Before Working

Read the matching documents below before changing or reviewing that area. Load only the topics
needed for the task; follow additional topics when a change crosses their boundaries. These files
carry repository instructions, not optional background. Do not preload the whole directory.

| Task or area | Read |
|---|---|
| Devices, hardware variants, kickstarts, boards or base-board templates | [Composition](docs/agents/composition.md) |
| Appliances, fixed wiring or hardware capability APIs | [Appliances](docs/agents/appliances.md) |
| Functional modules, shared device behavior or wMBus meters | [Modules](docs/agents/modules.md) |
| Board platform facts or GPIO/pin schemas | [Firmware platforms and pins](docs/agents/pins.md) |
| Wi-Fi, Ethernet, offline operation, time, API, OTA or mDNS | [Networking](docs/agents/networking.md) |
| Relay-backed switches/lights/valves, restoration or appliance relay adapters | [Relay control](docs/agents/relay-control.md) |
| Any YAML/package change, including substitutions, versions or templating | [Package design and YAML standards](docs/agents/package-design.md) |
| Dependency upgrades, custom components or upstream defects/workarounds | [Dependencies and pending workaround removals](docs/agents/dependencies.md) |

Keep this root file small: shared workflow and routing belong here; detailed contracts belong in
the linked topic files. Update the relevant topic when its contract changes. Do not duplicate these
files as nested `AGENTS.md` files or add instructions to read every topic unconditionally.

## Validation Standards

- Consumer README changes: run `python tests/docs_config.py` for complete examples and
  `python -m unittest discover -s tests -p 'test_*.py'` for local links/catalog coverage.
  The README runner mirrors this repository to checked-out packages and uses local components.
  Partial snippets still need their documented context; never treat an HA script as ESPHome YAML.

- YAML configuration-only changes: run `esphome config` only. Do not compile firmware for
  substitutions, metadata, package selection, or other configuration-only changes.
- C++ changes, including lambda bodies embedded in YAML: run config first, then compile only
  affected targets. Use focused host tests for behavioral logic. Do not compile the whole fleet.
- Devices must inherit logger thresholds from the base template. Keep hardware requirements such
  as `baud_rate: 0`; leave global/per-tag verbosity to the consuming ESPHome dashboard.
- Do not increment project versions for unpublished edits.

For local development, select checked-out components before ESPHome processes external sources:

```bash
cd devices
ESPHOME_LIB_SOURCE="$(pwd)/../components" esphome config sonoff-basic-r4.yaml
```

All declarations for this repository's components must include `packages/component-source.yaml`.
Without the environment variable, it selects the unpinned GitHub repository. Do not add self-repo
version pins or append a local source after a remote source (that still fetches the remote first).

The isolated regression suite uses dummy secrets and local components; run it with a Python
interpreter that has ESPHome installed. It performs no firmware compilation:

```bash
python tests/validate.py
python tests/validate.py --all
```

See `tests/README.md` for focused targets, host tests, known failures and CI behavior.

Choose validation targets by impact:

- Base-board, networking, or common diagnostics: validate at least one Wi-Fi ESPHome device and one relevant Ethernet or LibreTiny device.
- Pin wrapper changes: validate an ESPHome device and a LibreTiny device.
- Relay-control changes: validate a relay-control device and any device mode touched by the change.
- Device-only changes: validate that device.

When validation fails, report the first real error block and the file involved.

## Editing Discipline

- Inspect before editing.
- Change only files relevant to the task.
- Preserve unrelated user changes.
- Do not clean up generated ESPHome cache/build output unless explicitly asked.
- Do not rename, move, or reorganize packages unless explicitly asked.

## Reporting Back

Commit messages should describe the resulting change and relevant validation. Omit conversation
history, commit-splitting mechanics, and references to unpublished work in other commits.

When reporting changes:

- summarize what changed
- mention files changed
- include validation results or the first remaining error
- call out any ESPHome-version-specific workaround
