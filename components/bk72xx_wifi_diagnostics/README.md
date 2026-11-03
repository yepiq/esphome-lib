# BK7231N Wi-Fi receive diagnostics

Temporary diagnostics enabled by `devices/earu-breaker.yaml` for the investigation of
working broadcast delivery alongside failed ordinary unicast IPv4. This is instrumentation,
not a Wi-Fi fix or automatic recovery mechanism. Remove it when the investigation ends.

The linker wraps BDK's `ethernetif_input` without changing the vendor library. It observes
only the station interface and always forwards the original packet exactly once. A bounded
14-byte copy handles chained pbufs. It counts unicast and group-addressed IPv4, ARP and
EAPOL separately. Group means both broadcast and multicast. These are packets accepted
by the Beken driver, not over-the-air reception/decryption/drop counters.

The EARU configuration exposes:

- Six `WiFi RX …` cumulative packet counters, published every 10 seconds.
- `WiFi RX Snapshot`: exact integer counts, boot number and current LibreTiny sleep flag.
  Each protocol pair is `unicast/group`. Use this for probe deltas when large counts exceed
  the precision of ESPHome's float sensors.
- `WiFi Event History`: the six most recent station events, oldest first, including
  boot number, seconds since that boot and LibreTiny disconnect reason number.
  `up` means associated, `ip` means IP acquired; neither proves data reachability.
- `WiFi Diagnostic Snapshot`: immediately publishes/checkpoints the state and logs all
  12 retained events at INFO, including their sleep flags. Logger thresholds remain inherited.
- `WiFi Restart`: checkpoints the state, schedules local re-enable, then disables Wi-Fi
  for five seconds. Repeated presses during that interval are ignored. It does not reboot
  the MCU or command the relay, and requires no surviving connection to re-enable Wi-Fi.

Counters and the 12-event history use a fixed, versioned ESPHome preference key. They
survive normal reboots and OTA reflashes that retain preferences. Station transitions,
startup, a requested Wi-Fi restart and orderly shutdown are checkpointed immediately from
the main loop. Counts are also checkpointed every five minutes. Unexpected power loss can
lose counts since the last checkpoint; there is no per-packet flash write. A full flash erase
or factory reset clears the history. Uptime milliseconds wrap after about 49.7 days.

Callbacks only count packets or enqueue fixed-size events. Publishing and preferences
writes happen on the ESPHome main loop. A queue overflow is recorded as `lost`; its reason
field is the number of dropped events in that batch, capped at 255. The packet producer uses
atomic loads/stores because Beken ARMv5 does not support atomic read-modify-write instructions.

The EARU profile pins LibreTiny 1.13.0 and BDK 3.0.33 during this experiment; remove those
temporary pins together with the diagnostic configuration. The interface was inspected
against LibreTiny 1.13.0 and BDK 3.0.33. Other Beken chips are deliberately rejected until their
receive interfaces have been validated. Nothing is added to other device profiles.

At recurrence, take a snapshot, send labelled ordinary-unicast versus broadcast-carried IP
probes, and compare exact counters. Retrieve evidence before pressing Wi-Fi Restart. Recovery
would show a usable narrow intervention; it would not distinguish device state from AP
per-client state, since reconnect refreshes both.

Validation:

```sh
python components/bk72xx_wifi_diagnostics/tests/test_diagnostics.py
python tests/validate.py earu-acquisition
```

The host test runs the real C++ implementation under ASan/UBSan at `-O0` and `-O2`, with
SDK doubles for split packets, forwarding, interface filtering, event queue overflow,
counter wraparound, checkpointing, reboot/reflash restoration, and restart scheduling.
Also compile the EARU target and inspect the linked `rwm_upload_data` call to confirm it
reaches `__wrap_ethernetif_input`, which then calls the original `ethernetif_input`.
