# Command fan

Template-style speed fan with an `on_control` automation receiving `const fan::FanCall &x`
after native call validation, before state changes. Use `x.get_speed().has_value()` to distinguish an explicit speed
request from a plain On command, even when the requested speed matches the previous speed.
State publication retains native fan `on_state` behavior. Supported fields are state, speed
and oscillation; direction and presets are not exposed.

The initial speed is 1 so native FanCall validation does not invent a default High speed
for a plain On command. Restoration follows the configured native fan restore mode;
MCU-owned consumers should select `NO_RESTORE` and synchronize from MCU reports.

Pro Breeze uses the hook to remember an explicit startup speed, send power first, then
apply the speed on the MCU power acknowledgment. Its feedback guard prevents readback
calls from being treated as user intent. Repeated MCU power reports preserve the current
speed. A confirmed power cycle or plain On starts at Low; an explicit On with High applies
High after power acknowledgment, bypassing Tuya's stale pre-power-cycle speed cache.

Verified against ESPHome 2026.10.2: native `FanCall::validate_()` fills a missing speed only
when the fan's current speed is zero, and the template fan exposes resulting state rather
than command fields. Recheck these assumptions when upgrading ESPHome. This adapter can
be removed if the native template fan gains a command hook that preserves explicit speed
intent; retain the Pro Breeze startup and feedback regression checks when migrating.

Validate with `tests/fan_sync_host_test.py` and
compile `devices/pro-breeze-dehumidifier.yaml` after changes.
