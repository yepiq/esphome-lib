# Validation

Use the Python interpreter from your ESPHome environment. The CI baseline and the shared library
minimum are **ESPHome 2026.10.0**, which provides native conditional includes.

From the repository root:

```sh
python tests/validate.py                              # Consumer matrix and JSON models
python tests/validate.py --all                        # Also every tracked device/kickstart
python tests/validate.py source-tuya-product c3-light  # Named cases from cases.yaml
python tests/validate.py devices/jummico-dehumidifier.yaml
python -m unittest discover -s tests -p 'test_*.py'    # Runner and source-policy tests
python tests/docs_config.py                          # Complete consumer README examples
```

The runner invokes `esphome config`, never `esphome compile`. It copies working-tree content
to a fresh temporary directory, excludes secrets and caches, and supplies dummy secrets there.
Configurations with `secrets: false` have no secrets file anywhere in that copy. Device/kickstart
discovery for `--all` uses Git-tracked files; new public consumer combinations belong in `cases.yaml`.
Logs, the snapshot and `results.json` remain at the printed artifact path for inspection.
Third-party components and fonts can require network access. `ESPHOME_DATA_DIR` may select a
dedicated reusable test cache; otherwise the cache is temporary too.

The documentation runner reads complete YAML examples (with `substitutions.name` and `packages`)
from the root, device, package, module, networking and appliance READMEs. It mirrors this library's
remote package entries to an isolated working-tree copy, preserves include vars/custom tags, and
uses local custom components. This tests the example against the code being reviewed, not a stale
GitHub checkout. Partial snippets and the HA script example are not standalone ESPHome firmware;
they require their documented context. Unit tests also check local links and device catalog coverage.

## Local Components

Every external-component declaration for this library includes `packages/component-source.yaml`.
Its normal value is the unpinned `github://ngorchilov/esphome-lib`; remote ESPHome dashboard users
need no override. To use local components when working directly in a checkout:

```sh
cd devices
ESPHOME_LIB_SOURCE="$(pwd)/../components" esphome config jummico-dehumidifier.yaml
```

Use an absolute `components` path, and set it in the environment of the process actually running
ESPHome. This is an explicit development switch, not automatic local/remote package detection.
The runner sets it to the isolated snapshot's components and checks actual imported Python module
paths for every own-repository component. It also checks the unset-variable GitHub default without
fetching it. Adding a second local `external_components` entry is insufficient: ESPHome still
processes the original remote source first. Third-party component sources are not changed.

## Expected Results

- `PASS`: a supported configuration validates, including provenance checks where specified.
- `REJECTED`: a deliberately invalid configuration fails with its expected configuration error.
- `XFAIL`: a known bug remains reproducible. This is not a working/supported configuration.
- `XPASS`: a known bug unexpectedly validates; the run fails until its expectation is reviewed.
- `FAIL`: a new failure, wrong failure reason, rejected-input acceptance or subprocess timeout.

There are currently no `known_failure` cases. Offline networking now passes; devices that explicitly
need an absent clock or HA actions are covered by rejected-input tests rather than known failures.
The phase-2 regressions now pass, with resolved-output assertions for optional relay controls,
EARU sampling/units, packet-radio frequency and Wi-Fi credentials. Partial-secret fixtures supply
only the missing credential; this prevents an unused fallback secret from masking a regression.
Configuration validation does not prove actuator behavior or hardware safety. The six-zone valve
controller is a tracked shift-register bench draft again. Its YAML explicitly records pending
loaded-output polarity measurements and the unfinished button UX; its cloud model is not evidence
of a serial Tuya MCU.

The pin matrix covers ESP32 (classic, C3 and S3), ESP8266, Beken, Realtek and Lightning. It checks
the resolved GPIO options, explicit true/false values, shared inputs, open-drain outputs, ESP32
drive strength and strapping flags, and number-only mappings through ESPHome's pin-number
validator. Concrete Ethernet devices exercise number-only consumers in the full sweep. Invalid
schema names and unsupported ESP8266 pullups must fail; ESP8266 relay roles must now pass.

The ceiling-light cases cover V1 CBU and both V2 module profiles. Resolved-output checks verify
V2 board selection, RGB/white pin mappings, PWM frequency and driver, full output limits, and
shared white mixing. The chip substitution is exercised independently of the device filename;
an unsupported module must fail configuration.

The device-family cases cover CB2S/T1-M CT meters and CBU/T1-U 4PM strips, including standalone
defaults, include vars, channel names, UART overrides and custom relay IDs. Assertions preserve
Tuya datapoints/scaling, T1-M-only alarms, fixed wiring, relay restoration and master-button/power-cycle
commands. Unsupported profiles are rejected even when their names identify another valid board.

Shared-behavior cases cover both strip products, isolated relay groups and fan facades in one
firmware, missing prerequisites, invalid group membership, both dehumidifier interfaces and all
16 CT16 channels. Channel overrides exercise names, scaling, per-channel visibility and solar
visibility. The CT16 raw decoder stays device-local and unchanged by the channel extraction.

The RF fan matrix covers SX127x and CC1101, explicit IDs and shorthand addresses, combined fan
membership, individual-only and learn-only configurations, all four synchronization anchors, and
custom protocol settings. Resolved-output assertions check entity metadata, each member's generated
address/ID/direction, startup and queue guards, synchronization commands, and transmission timing.
These are configuration contracts, not proof of RF reception or physical fan state. When rewriting
the templates, compare the resolved configurations (including lambda text) before and after; an
unchanged emitted C++ program does not need a firmware build.

Networking checks cover offline ESP32/ESP8266/Beken/Realtek, local relay control, explicit RTC time
for Tuya and integrated RTC appliances, both dual-interface priorities, disabled services, interface
startup policy, distinct IP/MAC diagnostics, and appliance forwarding. Invalid selectors, service
dependencies, boolean options and missing clocks are rejected. Config validation does not test
physical cable failover, radio association or HA reconnection; those need hardware verification.

Every passing configuration also checks that `esphome.min_version` is the highest contributed
`esphome_requirements` version, using ESPHome's own version parser as an independent reference.
The source-policy tests scan YAML structure (including inline/conditional packages) to enforce
the shared base template as the sole writer. Configuration cases cover package order, repeated
and nested includes, dashboard additions, disabled features, LCD/network combinations and the
MELcutter/base collision. Invalid declarations and too-new month/patch versions must be rejected.
These checks use config validation only; they do not require a firmware build.

All CI configuration checks run on 2026.10.0. Version-composition cases retain independent feature
requirements below the shared floor and reject numerically ordered future requirements above it.
The RF receiver cases check byte-sized buffers on ESP32, ESP8266 and Beken, explicit overrides,
both dry-relay consumers, and a disabled receiver with an intentionally invalid unused pin.

The Model 716 thermostat cases validate the generic BK7231N Tuya board and a UART baud override.
Its cloud-based profile still needs physical UART, range and feature verification. The host test
executes the device's actual lambdas to check command datapoints, feedback ordering, read-only
valve activity, fault bits, temperature scaling and the battery-absent sentinel:

```sh
python tests/thermostat_host_test.py
```

## C++ And CI

YAML configuration-only changes require config validation only. Compile firmware only after
changing C++, including lambda bodies in YAML, and only for affected targets after config passes.
Host tests supplement this; they do not replace an affected embedded build or hardware verification.

The fan synchronization test resolves the current device packages in an isolated snapshot with
dummy secrets and local components. It translates the small supported YAML action subset to host
C++, executes the actual device lambdas with ASan/UBSan, and checks 224 command combinations plus
MCU readback, feedback suppression, boot-speed behavior and unavailable-speed handling:

```sh
python tests/fan_sync_host_test.py
```

Run this when changing fan command behavior, followed by config/compile of Pro Breeze and JUMMICO.
The host doubles do not simulate UART timing or the physical appliances.

The garage regression compiles the actual YAML lambdas with ASan/UBSan, checking commands after
boot/external operation, contact-confirmed close, explicit retries after timeouts, endpoint/pulse
guards, timeout publication, wraparound and the BLE reboot interlock:

```sh
python tests/garage_host_test.py
```

Run it when changing garage C++ behavior, then config/compile both the standalone garage and
`tests/fixtures/garage-ble.yaml`. These host tests are deliberately separate from the config-only
CI workflow, so routine YAML configuration edits do not trigger firmware or host compilation.

The existing BLE host suite tests the checked-out implementation with ASan/UBSan and an SDK double:

```sh
python components/bk72xx_ble_server/tests/test_recovery.py
```

The Beken UART guard has a focused host suite for interrupt exclusion, both serial ports,
overflow detection, persistent totals and source filtering when no UART is configured:

```sh
python components/bk72xx_uart_guard/tests/test_uart_guard.py
```

Guard changes also require BK7231N and BK7238 firmware builds, plus inspection of the actual
Serial vtable and ARM mask/restore instructions. Build a UART-free Beken target to verify that
the guard sources and wrapper flag are absent. The CT16 config cases include a dashboard-style
consumer and retain the actual 256-byte buffer while monitoring overflow.

It requires `clang++` (or `CXX` pointing to a compatible compiler), and builds only a small host
executable, not firmware. CI runs the config matrix, all tracked devices/kickstarts and JSON checks
on pushes/PRs. The separate BLE host job runs for changes to that component or its tests, or on
manual dispatch. Neither workflow compiles firmware. Changes to embedded C++ still require the
focused embedded build above and its result in the change report.
