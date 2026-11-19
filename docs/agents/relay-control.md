# Relay-Control Framework

Read for: Relay roles, POWER/CONTROL/PRIMARY, restoration and appliance relay adapters.

These instructions supplement [AGENTS.md](../../AGENTS.md). Paths and YAML examples are
relative to the repository root unless stated otherwise.

## Relay-Control Framework

`packages/modules/relay-control.yaml` is the public entrypoint for reusable relay-backed switch,
light, and valve behavior. It is an assembler package: it composes core relay behavior, one entity
type, one control target, and optional feature packages.

Relay-control concepts:

- POWER is the local physical relay output plus its logical state and command scripts.
- CONTROL is the logical target for external inputs and optional entity facades.
- CONTROL may map to POWER locally, call a detached Home Assistant entity, or remain no-op.
- ENTITY is the complete user-facing role configuration under `rc.entity`.
- PRIMARY is the command path that operates the selected ENTITY.

Supported `rc.entity.type` values:

- `switch` (default): use an output-backed switch as the POWER state owner and primary entity.
- `light`: for local control, use a binary light as the POWER state owner and drive the GPIO output
  directly. Detached lights and lights with separately exposed power use an output-backed POWER
  switch plus a CONTROL light facade.
- `valve`: retain an output-backed POWER switch as the state and restoration owner, then expose a
  binary CONTROL valve facade that reports that POWER state as open or closed.

Unsupported entity types and control modes must fail configuration. Do not add fallback branches
that silently turn misspelled enum values into another behavior.

Valve entities accept an optional `rc.entity.device_class` (`water`, `gas`, or empty). Do not assign
a generic valve device class when the physical medium is unknown.

Hardware profiles should describe fixed pins and physical features once, then forward the caller's
complete `entity` vars object as `rc.entity`. Do not unpack entity fields in each hardware profile.
Add future entity types such as fans to relay-control itself; hardware profiles must remain unchanged.

Single-relay device profiles expose this package API:

```yaml
files:
  - path: devices/tuya-mini-switch-1dc-5a.yaml
    vars:
      entity:
        type: valve
        name: Main Water Valve
        device_class: water
```

Omitting `entity` produces the default unnamed switch. Valve entities hide their backing power
switch by default. Local light entities do not create a backing switch unless it is needed;
`rc.entity.power.exposed: true` creates and exposes one separately, and `rc.entity.power.name` sets
its name. `rc.entity.icon` applies to the selected switch, light, or valve facade; a separately
exposed backing power switch uses `rc.entity.power.icon`. `rc.entity.enabled: false` suppresses the
facade, state owner, control scripts, and optional features while retaining the selected provider's
physical output. `rc.power.output_id` optionally overrides the physical output id, which otherwise
defaults to `${rc.id}_power_output`.

The default `rc.power.provider: gpio` creates that output from `rc.power.pin`. Appliance packages may
instead use `rc.power.provider: external`; the appliance must create the binary output itself and
pass its id through `rc.power.output_id`. This keeps fixed expander wiring in the appliance while
reusing the same entity and control behavior.

Core invariants:

- The local binary output is always present; a switch facade is created only when the selected role
  needs one.
- Exactly one component owns restored POWER state: an output switch, or a direct local binary light.
- `${rc.id}_power_state` is the stable internal binary sensor for observing POWER independently of
  its owner type. Device packages must not inspect `${rc.id}_power_relay` directly.
- `${rc.id}_power_on`, `${rc.id}_power_off`, and `${rc.id}_power_toggle` are the stable commands for
  operating POWER. Device packages must use these scripts instead of addressing the owner directly.
- Valve facades publish OPEN or CLOSED from the POWER state hooks so startup consumers never observe
  ESPHome's temporary default valve state.
- A POWER switch defaults to `None` when it is the primary switch entity. POWER remains independently
  controllable through its stable scripts even when CONTROL is detached.
- Indicator LEDs, when present, follow POWER state for safety.
- Integrated physical buttons, when present, toggle POWER.
- External wall-switch inputs toggle PRIMARY so facade state remains synchronized.
- Valve and adapter-style light entities target CONTROL while their POWER switch remains independent.
- The optional power-cycle feature exposes a template button backed by an `${rc.id}_power_cycle`
  script. The off-time defaults to `3s`; `rc.power_cycle.delay` overrides it when needed.

Relay-control exposes `${rc.id}_primary_on`, `${rc.id}_primary_off`, and
`${rc.id}_primary_toggle` scripts for physical inputs. Primary switch commands delegate directly to
CONTROL. Valve and adapter-style light commands operate their facade, which delegates the resulting
state to CONTROL; a direct local light owns POWER itself. Device-specific input components should
call these PRIMARY scripts rather than bypassing the selected facade.

`rc.entity.control.mode` values:

- `local`: CONTROL delegates to POWER.
- `detached`: CONTROL calls Home Assistant service/action on `rc.entity.control.entity_id`.
- `none`: CONTROL scripts remain no-op.

Low-level callers may define the same defaults under `rc.control`; values under `rc.entity.control`
take precedence.

Relay-control is multi-instance by design. Every generated id must include `rc.id` or another
caller-provided unique prefix. Do not move instance-specific values into global substitutions unless
there is no workable alternative.

Preferred include shape:

```yaml
packages:
  - !include
    file: ../packages/modules/relay-control.yaml
    vars:
      rc:
        id: r1
        entity:
          type: switch
          name: None
        power:
          pin: GPIO4
          inverted: false
          strapping: false
        control:
          mode: local
        power_cycle:
          enabled: true
          name: Power Cycle
```
