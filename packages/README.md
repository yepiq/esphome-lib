# ESPHome Version Requirements

Board-backed firmware automatically selects the highest ESPHome version required by its included
packages. You do not need to calculate a combined minimum when adding a display, networking or an
optional feature.

The shared base requires **2026.10.0** for native conditional includes. Feature requirements still
merge independently: clock-backed uptime contributes 2026.6.0, the Waveshare LCD 7B contributes
2026.7.0, and dual networking contributes 2026.8.0. These older requirements cannot reduce the
base's minimum. Disabling a feature removes its contribution; a future feature requiring a newer
release will raise the resolved minimum automatically.

This is the **ESPHome tool version**, not your firmware's `esphome.project.version`, SDK version,
or a record of which version was used for testing.

## Dashboard Configuration

Normally, include your device without any version override. When your dashboard adds functionality
that needs a newer ESPHome release, add a requirement alongside the device package:

```yaml
substitutions:
  name: wall-panel
  friendly_name: Wall Panel
  esphome_requirements:
    - source: my-dashboard
      version: 2026.8.0

packages:
  - url: https://github.com/yepiq/esphome-lib
    ref: main
    refresh: 0d
    files:
      - devices/waveshare-esp32-s3-touch-lcd-7b.yaml
```

Each entry accepts exactly these fields:

| Field | Meaning |
| --- | --- |
| `source` | Nonempty label identifying the package or feature that needs this version. |
| `version` | A released version in `major.minor.patch` form, such as `2026.8.0`. |

Requirements combine as a list, not a dictionary keyed by source. Repeated entries are harmless;
even different versions with the same source label are retained and the highest wins. Comparison
is numeric: `2026.10.0` is newer than `2026.9.0`. Malformed entries, version ranges, and prerelease
or `dev` requirement strings are rejected rather than interpreted approximately.

**Do not set `esphome.min_version` directly**, either in your dashboard or another package. ESPHome
can let that scalar override the calculated result, including lowering it. Remove such overrides
and add their requirements to this list instead. Likewise, do not replace `esphome_requirements`
using a CLI substitution or pass it as an include var. The library does not intercept deliberate
overrides of native ESPHome configuration.

Run `esphome config` on your dashboard YAML. Its output shows the contributing requirements under
`substitutions.esphome_requirements` and the selected result under `esphome.min_version`. An older
installed ESPHome version fails validation with the required upgrade version.

## Adding Packages

Custom packages use the same `substitutions.esphome_requirements` list. Declare only what that
package needs; there is no central feature/version table to edit. A package with no extra requirement
can omit the list. The common base owns the one resolver and always contributes its library floor.

For an optional feature, place its requirement in the package that is included only when enabled,
alongside that feature's component configuration. A disabled feature must not leave an unconditional
requirement in its parent package. Nested and repeated includes are supported, and package order
does not affect the highest requirement.

Third-party packages must follow the same contract when combined with this library. Their native
`esphome.min_version` declarations are not automatically converted into contributions. Independent
component schema checks still apply; this registry cannot infer version requirements from arbitrary
component code or validate hardware compatibility.
