# Package Design Standards

Read for: Any YAML or package change: version requirements, vars, IDs, includes, style and templating.

These instructions supplement [AGENTS.md](../../AGENTS.md). Paths and YAML examples are
relative to the repository root unless stated otherwise.

## Package Design Standards

### ESPHome Version Requirements

`packages/boards/templates/base-board.yaml` is the sole writer of `esphome.min_version`. Each
device/module/feature contributes its own minimum through the additive global list:

```yaml
substitutions:
  esphome_requirements:
    - source: waveshare_io_ch32v003
      version: 2026.7.0
```

Use released `major.minor.patch` strings and a nonempty feature/source label. The base resolver
validates the entries and compares numeric version triples after package requirements have merged.
Lists concatenate, including repeated/nested includes; never replace the registry with a scalar
or a source-keyed mapping. Requirements are global facts, not module vars or defaults. Put an
optional feature's contribution inside its selected package so disabling it removes the requirement.
Packages with no additional requirement contribute nothing. Do not enumerate other modules' needs
or inspect networking in an appliance to calculate its version. The base contributes the library
floor independently of device-specific requirements.

Dashboard requirements use the same list. A native top-level `esphome.min_version` overrides the
resolver under ESPHome's merge rules and is outside this contract. CI scans YAML for other writers
and checks every passing config's resolved minimum against its complete requirement list. Keep the
resolver inline in the shared base template; no Python component or one-use include is needed.
See `packages/README.md` for the consumer contract and dashboard example.

### Defaults, Vars, And Substitutions

- Public reusable module APIs must use one namespaced object under `vars:` such as `rc:`, `pin:`,
  `networking:`, or `energy:`.
- Use `defaults:` to normalize namespaced objects into local helper values inside the module.
- Use guarded lookups such as `rc.get("power", {}).get("pin", "GPIO0")`; do not rely on deep
  default merging.
- Use global `substitutions:` for device-local aliases, names, friendly names, board facts, and
  ESPHome values that are intentionally global.
- Avoid global substitutions for reusable module inputs.
- Internal package references may use private-looking names such as `_rc_target_local_pkg`.
- Keep defaults close to the module that owns them.

### IDs And Names

- Generated ids in reusable modules must be deterministic and collision-safe.
- Multi-instance modules must include an instance prefix such as normalized `rc_id` in every
  generated id.
- Internal id prefixes must not leak into user-facing entity names. Give entities neutral defaults
  and expose an explicit module name option when callers may need another label.
- Shared base-board diagnostics may use stable `mcu_*` ids.
- Single-instance modules may use simple ids only when the module is clearly not multi-instance.
- When a device has one obvious primary entity, prefer `name: None` so Home Assistant presents it
  using the device name. Ask before selecting a primary entity when the choice is ambiguous.
- Do not change entity names just because they look odd. Some names intentionally influence Home
  Assistant display behavior.

### Optional Features

- Optional subcomponents should be opt-in and easy to disable.
- Prefer clear namespaced booleans such as `rc.indicator_led.enabled`,
  `rc.external_switch.enabled`, or `rc.power_cycle.enabled`.
- Disabled optional packages should contribute no components.
- Feature flags should not require callers to pass irrelevant pins or entity ids.

### Includes And Conditional Packages

- Prefer list-form `packages:` entries:

```yaml
packages:
  - !include ../packages/modules/example.yaml
```

- Use real `!include` blocks with `vars:` when passing module variables.
- Be careful with named package entries; use them only when they are clearly needed.
- Do not return raw `{file: ..., vars: ...}` package dictionaries from expressions.
- Validate conditional include behavior with `esphome config` before applying it broadly.

The library floor is ESPHome 2026.10.0. Use native `!include` blocks with `condition:` for
optional file-backed packages, preserving their existing vars and ids. Keep unique inline
device behavior inline; conditional includes do not justify extracting one-use files.

## YAML Coding Standards

- Avoid quotes unless YAML requires them.
  - Empty string values may use `''`.
  - Plain values such as `local`, `detached`, `rocker`, `light.turn_on`, and `RESTORE_DEFAULT_OFF` should remain unquoted.
- Preserve existing quoted values when they appear intentional.
- Prefer readable YAML over compact one-liners.
- Keep comments short and useful.
- Do not add explanatory comments for obvious YAML.
- Let `device_class` select the default Home Assistant icon. Set `icon` only for an intentional
  override or when the entity has no suitable device class.

ESPHome component attribute order:

```text
platform
name
id
visibility/internal/entity category
pin/output/entity-specific options
automations/actions
```

When both `name` and `id` are present, prefer `name` before `id`.

## ESPHome Templating Standards

ESPHome templating behavior depends on version and context. Be conservative.

Known fragile patterns:

- returning schema-sensitive mappings from `${ ... }`
- using dynamic paths inside nested `!include` wrappers
- using YAML merge (`<<`) with `${ ... }` values
- returning raw package dictionaries with `file` / `vars` from expressions
- relying on named package entries where list-form entries are clearer

If a templating approach is required for reusable infrastructure, validate it with `esphome config`
on concrete ESPHome and LibreTiny devices when applicable.

The RF fan device keeps its per-address entity generation and captured C++ blocks inline. Prefer
readable template blocks to assembling C++ one quoted line at a time. For template-only rewrites,
compare resolved configuration and lambda text to confirm that emitted C++ is unchanged; the RF
consumer matrix in `tests/cases.yaml` covers both radios and the supported fan composition options.
