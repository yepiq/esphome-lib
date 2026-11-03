"""Assertions about resolved configuration, beyond schema validity."""

import json
from pathlib import Path
import sys

from esphome import config_validation as cv, pins
from esphome.config import path_context, read_config
from esphome.core import CORE


def entity(config, domain, name):
    return next(item for item in config.get(domain, []) if str(item.get("id")) == name)


def ids(config, domain):
    return {str(item["id"]) for item in config.get(domain, []) if "id" in item}


def enabled(value):
    return str(value).lower() == "true"


def check_ct2(config, substitutions):
    profile = substitutions.get("test_profile", "cb2s")
    assert config["bk72xx"]["board"] == ("t1-m" if profile == "t1m" else "cb2s")
    uart = entity(config, "uart", "tuya_uart")
    for key, default in (("tx_pin", "GPIO11"), ("rx_pin", "GPIO10")):
        assert uart[key]["number"] == int(substitutions.get(f"uart_{key}", default).removeprefix("GPIO"))
    assert uart["baud_rate"] == int(substitutions.get("uart_baud_rate", 9600))
    assert str(config["tuya"]["uart_id"]) == "tuya_uart"
    assert str(config["tuya"]["time_id"]) == "ha_time"
    channels = {c: substitutions.get(f"test_channel_{c}_name", f"Channel {c.upper()}") for c in "ab"}
    for channel, label in channels.items():
        assert entity(config, "text_sensor", f"current_flow_{channel}")["name"] == f"Flow Direction {label}"
        for prefix, name, unit, decimals, device_class, state_class in (
            ("power", "Power", "W", 1, "power", "measurement"),
            ("current", "Current", "A", 3, "current", "measurement"),
            ("power_factor", "Power Factor", "%", 0, "power_factor", "measurement"),
            ("energy_consumed", "Energy Consumed", "kWh", 2, "energy", "total_increasing"),
            ("energy_produced", "Energy Produced", "kWh", 2, "energy", "total_increasing"),
        ):
            sensor = entity(config, "sensor", f"{prefix}_{channel}")
            assert sensor["name"] == f"{name} {label}"
            assert (sensor["unit_of_measurement"], sensor["accuracy_decimals"]) == (unit, decimals)
            assert (sensor["device_class"], sensor["state_class"]) == (device_class, state_class)
    callbacks = {item["sensor_datapoint"]: item for item in config["tuya"]["on_datapoint_update"]}
    scaled = {101: ("power_a", "power_scale"), 105: ("power_b", "power_scale"),
              106: ("energy_consumed_a", "energy_scale"), 107: ("energy_produced_a", "energy_scale"),
              108: ("energy_consumed_b", "energy_scale"), 109: ("energy_produced_b", "energy_scale"),
              111: ("frequency", "frequency_scale"), 112: ("voltage", "voltage_scale"),
              113: ("current_a", "current_scale"), 114: ("current_b", "current_scale"),
              115: ("total_power", "power_scale"), 130: ("energy_consumed", "energy_scale"),
              131: ("energy_produced", "energy_scale")}
    assert callbacks.keys() == scaled.keys() | {102, 104, 110, 121}
    for dp, (name, scale) in scaled.items():
        assert callbacks[dp]["datapoint_type"] == "int"
        body = callbacks[dp]["then"][0]["lambda"].value
        assert body == f"id({name}).publish_state(x * {config['substitutions'][scale]});"
    for dp, channel in ((102, "a"), (104, "b")):
        body = callbacks[dp]["then"][0]["lambda"].value
        assert callbacks[dp]["datapoint_type"] == "enum" and "if (x == 0)" in body
        assert f'id(current_flow_{channel}).publish_state("Forward");' in body
        assert f'id(current_flow_{channel}).publish_state("Reverse");' in body
    for dp, channel in ((110, "a"), (121, "b")):
        assert callbacks[dp]["then"][0]["lambda"].value == f"id(power_factor_{channel}).publish_state(x);"
    numbers = {item["number_datapoint"]: item for item in config["number"]}
    assert (numbers[129]["min_value"], numbers[129]["max_value"], numbers[129]["step"]) == (3, 60, 1)
    alarms = [item for item in config["binary_sensor"] if item["platform"] == "tuya"]
    switches = [item for item in config.get("switch", []) if item["platform"] == "tuya"]
    if profile == "t1m":
        assert numbers.keys() == {129, 137, 138, 139, 140, 145, 146}
        assert {item["sensor_datapoint"] for item in alarms} == {141, 142, 143, 144, 147, 148}
        assert {item["switch_datapoint"] for item in switches} == {132, 133, 134, 135, 136, 149, 150}
        assert all(item["entity_category"] == "config" for dp, item in numbers.items() if dp != 129)
        assert all(item["entity_category"] == "config" for item in switches)
        assert all(item["entity_category"] == "diagnostic" and item["device_class"] == "problem" for item in alarms)
        boot = next(item for item in config["esphome"]["on_boot"] if item["priority"] == 800)
        body = boot["then"][0]["lambda"].value
        assert all(f"id({item['id']}).publish_state(false);" in body for item in alarms)
    else:
        assert numbers.keys() == {129} and not alarms and not switches
        assert not any(item["priority"] == 800 for item in config["esphome"]["on_boot"])


def check_relay_group(config, group, relays, state_id, indicator_id):
    status = entity(config, "binary_sensor", state_id)
    assert "".join(status["lambda"].value.split()) == "return" + "||".join(f"id({r}_power_state).state" for r in relays) + ";"
    indicator = status["on_state"][0]["then"][0]["if"]
    assert str(indicator["condition"]["binary_sensor.is_on"]["id"]) == state_id
    assert str(indicator["then"][0]["light.turn_on"]["id"]) == indicator_id
    assert str(indicator["else"][0]["light.turn_off"]["id"]) == indicator_id
    boot = next(hook["then"][0]["if"] for hook in config["esphome"]["on_boot"]
                if hook["priority"] == -100 and "if" in hook["then"][0]
                and str(hook["then"][0]["if"].get("condition", {}).get("binary_sensor.is_on", {}).get("id")) == state_id)
    assert str(boot["then"][0]["light.turn_on"]["id"]) == indicator_id
    assert str(boot["else"][0]["light.turn_off"]["id"]) == indicator_id
    action = entity(config, "script", f"{group}_toggle")["then"][0]["if"]
    assert str(action["condition"]["binary_sensor.is_on"]["id"]) == state_id
    for branch, command in (("then", "off"), ("else", "on")):
        assert [str(item["script.execute"]["id"]) for item in action[branch]] == [f"{r}_power_{command}" for r in relays]
    reboot = entity(config, "button", f"{group}_cycle")
    assert [str(item["script.execute"]["id"]) for item in reboot["on_press"][0]["then"]] == [f"{r}_power_cycle" for r in relays]


def check_strip4(config, substitutions):
    profile = substitutions.get("test_profile", "cbu")
    is_cbu = profile == "cbu"
    assert config["bk72xx"]["board"] == ("cbu" if is_cbu else "t1-u")
    pins = [6, 7, 8, 9, 26] if is_cbu else [26, 9, 24, 21, 6]
    relays = [substitutions.get(f"relay{i}_id", f"socket_{i}" if i < 5 else "relay_usb") for i in range(1, 6)]
    for i, (prefix, pin) in enumerate(zip(relays, pins), 1):
        output = entity(config, "output", f"{prefix}_power_output")
        assert output["pin"]["number"] == pin and not output["pin"]["inverted"]
        relay = entity(config, "switch", f"{prefix}_power_relay")
        assert relay["name"] == substitutions.get(f"relay{i}_name", f"Socket {i}" if i < 5 else "Relay USB")
        assert relay["restore_mode"] == "RESTORE_DEFAULT_OFF"
        assert {f"{prefix}_power_{command}" for command in ("on", "off", "cycle")} <= ids(config, "script")
    led = entity(config, "output", "led_output")
    assert led["pin"]["number"] == (20 if is_cbu else 23) and not led["inverted"]
    status = entity(config, "binary_sensor", "power_status")
    assert status["name"] == "Power Status"
    check_relay_group(config, "strip_power", relays, "power_status", "status_led")
    button = next(item for item in config["binary_sensor"] if item["platform"] == "gpio")
    assert button["pin"]["number"] == 22 and button["pin"]["inverted"] and button["pin"]["mode"]["pullup"]
    assert str(button["on_press"][0]["then"][0]["script.execute"]["id"]) == "strip_power_toggle"
    energy = config["substitutions"].get("test_energy", {})
    meter = entity(config, "sensor", "energy_monitor")
    assert meter["platform"] == "bl0942"
    assert meter["update_interval"] == cv.positive_time_period_milliseconds(energy.get("update_interval", "30s"))
    assert meter["energy"]["unit_of_measurement"] == "kWh"
    assert config["uart"][0]["baud_rate"] == energy.get("baud_rate", 4800)
    assert (config["uart"][0]["tx_pin"]["number"], config["uart"][0]["rx_pin"]["number"]) == (11, 10)
    if "test_networking" in substitutions:
        assert not {"wifi", "ethernet", "network", "api", "ota", "mdns"} & config.keys()


def check_ct16(config, substitutions):
    for number in range(1, 17):
        name = substitutions.get(f"c{number:02d}_name", f"C{number:02d}")
        internal = enabled(substitutions.get(f"c{number:02d}_internal", False))
        for suffix, label, unit, device_class, decimals in (
            ("current", "Current", "A", "current", 3), ("power", "Power", "W", "power", 0),
        ):
            sensor = entity(config, "sensor", f"circuit_{number}_{suffix}")
            assert sensor["name"] == f"{name} {label}" and sensor["internal"] == internal
            assert (sensor["unit_of_measurement"], sensor["device_class"], sensor["accuracy_decimals"]) == (unit, device_class, decimals)
            assert sensor["state_class"] == "measurement"
        energy = next(item for item in config["sensor"] if item.get("sensor_datapoint") == 114 + number)
        assert energy["name"] == f"{name} Energy" and energy["internal"] == internal
        assert str(energy["tuya_id"]) == "my_meter"
        assert (energy["unit_of_measurement"], energy["state_class"], energy["accuracy_decimals"]) == ("kWh", "total_increasing", 2)
        assert energy["filters"][0]["multiply"] == float(substitutions.get("energy_scale", 0.01))
        assert energy["filters"][1]["clamp"]["min_value"] == 0
        assert energy["filters"][1]["clamp"]["max_value"] == 20000000
        detected = entity(config, "binary_sensor", f"circuit_{number}_ct_detected")
        solar = entity(config, "binary_sensor", f"circuit_{number}_solar_configured")
        assert detected["name"] == f"{name} CT Clamp" and detected["internal"] == internal
        assert solar["name"] == f"{name} Solar Mode"
        assert solar["internal"] == (internal or enabled(substitutions.get("sol_internal", False)))
        assert detected["entity_category"] == solar["entity_category"] == "diagnostic"
        assert detected["device_class"] == "plug" and solar["icon"] == "mdi:solar-power"
    assert len([s for s in config["sensor"] if s.get("sensor_datapoint", 0) in range(115, 131)]) == 16
    uart = entity(config, "uart", "tuya_uart")
    assert uart["baud_rate"] == 115200 and uart["rx_buffer_size"] == 256
    assert "bk72xx_uart_guard" in config
    assert "LT_SERIAL_BUFFER_SIZE" not in config["bk72xx"]["framework"]["options"]
    assert "tuya_uart_rx_overflows" not in ids(config, "sensor")
    assert not any(item["platform"] == "bk72xx_uart_guard" for item in config["sensor"])
    assert not any(item.get("on_time") for item in config.get("time", []))


def check_fan_power(config, fan_id, power_id, condition):
    fan = entity(config, "fan", fan_id)
    action = fan["on_state"][0]["then"][0]["if"]
    assert action["condition"]["lambda"].value == condition
    power = action["then"][0]["if"]
    assert power["condition"]["lambda"].value == "return x->state;"
    for branch, state, command in (("then", "off", "on"), ("else", "on", "off")):
        change = power[branch][0]["if"]
        assert str(change["condition"][f"switch.is_{state}"]["id"]) == power_id
        assert str(change["then"][0][f"switch.turn_{command}"]["id"]) == power_id
    assert len(power["else"]) == 1
    return power["then"][1:]


def check_dehumidifier(config):
    jummico = "jummico_fan" in ids(config, "fan")
    prefix = "jummico" if jummico else "pb"
    fan = entity(config, "fan", f"{prefix}_fan")
    assert fan["name"] == "" and not fan.get("internal", False) and fan["speed_count"] == 2
    assert fan["has_oscillating"] == (not jummico)
    assert fan["restore_mode"] == "RESTORE_DEFAULT_OFF"
    running = check_fan_power(config, f"{prefix}_fan", f"{prefix}_power_dp",
                              "return !id(jummico_syncing_fan);" if jummico else "return true;")
    assert len(running) == 1 and "const int want_speed" in running[0]["lambda"].value
    callbacks = {dp["sensor_datapoint"]: dp for dp in config["tuya"]["on_datapoint_update"]}
    assert callbacks.keys() == ({1, 4, 19} if jummico else {1, 6, 8, 11})
    assert callbacks[1]["datapoint_type"] == "bool"
    assert callbacks[4 if jummico else 6]["datapoint_type"] == "enum"
    for label in ("Mode", "Countdown"):
        assert next(s for s in config["select"] if s["name"] == label)["entity_category"] == "config"
    assert next(s for s in config["switch"] if s["name"] == "Child Lock")["entity_category"] == "config"
    power = entity(config, "switch", f"{prefix}_power_dp")
    assert power["internal"] and power["switch_datapoint"] == 1
    faults = [s for s in config["binary_sensor"] if s.get("name", "").startswith("Fault:")]
    assert len(faults) == (8 if jummico else 6)
    assert all(s["entity_category"] == "diagnostic" and s["device_class"] == "problem" for s in faults)
    assert config["esphome"]["project"]["version"] == ("0.1.0" if jummico else "0.9.0")
    assert config["logger"]["level"] == "INFO" and config["logger"]["baud_rate"] == 0


def check_fan433(config, substitutions):
    learn_only = config["esphome"]["name"] == "fan-control-433"
    if learn_only:
        fans = []
    elif enabled(substitutions.get("test_shorthand", False)):
        fans = [(0x0000, "fan_0000", "Fan 0000"), (0xFFFF, "fan_ffff", "Fan FFFF")]
    else:
        fans = [(0x1234, "supply_fan", "Supply Fan"), (0x2345, "extract_fan", "Extract Fan")]
    combined = not learn_only and enabled(substitutions.get("test_combined", True))
    expected_ids = {name for _, name, _ in fans} | ({"ventilation"} if combined else set())
    assert ids(config, "fan") == expected_ids
    assert {str(item["id"]) for item in config["button"] if str(item.get("id", "")).endswith("_synchronize")} == {
        f"{name}_synchronize" for _, name, _ in fans
    }

    speed_count = substitutions.get("fan_speed_count", 6)
    direction_out = substitutions.get("fan_direction_out", "FORWARD")
    direction_in = substitutions.get("fan_direction_in", "REVERSE")
    commands = {name: substitutions.get(f"fan_cmd_{name}", default) for name, default in {
        "on": 0x0A, "off": 0x0D, "out_plus": 0x0B, "out_minus": 0x0C,
        "in_plus": 0x0E, "in_minus": 0x0F,
    }.items()}
    sync_direction = substitutions.get("fan_sync_direction", "out")
    sync_min = substitutions.get("fan_sync_endpoint", "min") == "min"
    sync_command = commands[f"{sync_direction}_{'minus' if sync_min else 'plus'}"]
    boot = next(hook for hook in config["esphome"]["on_boot"] if hook["priority"] == -100)["then"][0]["lambda"].value
    assert f"static_assert(fan::FanDirection::{direction_out} != fan::FanDirection::{direction_in});" in boot
    assert boot.rstrip().endswith("id(fan433_ready) = true;")
    for address, name, label in fans:
        fan = entity(config, "fan", name)
        assert fan["name"] == label and fan["has_direction"]
        assert fan["speed_count"] == speed_count
        assert fan["restore_mode"] == substitutions.get("fan_restore_mode", "RESTORE_DEFAULT_OFF")
        action = fan["on_state"][0]["then"][0]["if"]
        assert action["condition"]["lambda"].value == "return id(fan433_ready);"
        transmit = action["then"][1]["if"]
        assert transmit["condition"]["lambda"].value == (
            "return !id(fan433_batch_active) && !id(fan433_command_queue).empty() && !id(fan433_transmit_active);"
        )
        assert str(transmit["then"][0]["script.execute"]["id"]) == "fan433_transmit_queue"
        body = action["then"][0]["lambda"].value
        synchronize = entity(config, "button", f"{name}_synchronize")
        assert synchronize["name"] == f"{label} Synchronize"
        assert synchronize["entity_category"] == "config"
        sync = synchronize["on_press"][0]["then"][0]["lambda"].value
        for code in (body, sync, boot):
            assert f"const uint16_t address = 0x{address:04X};" in code
            assert f"std::min({speed_count}, id({name}).speed)" in code
            assert f"id({name}).direction == fan::FanDirection::{direction_out}" in code
        for code in (body, sync):
            assert f"const bool target_on = id({name}).state;" in code
            assert f"const uint8_t plus_command = target_out ? {commands['out_plus']} : {commands['in_plus']};" in code
            assert f"const uint8_t minus_command = target_out ? {commands['out_minus']} : {commands['in_minus']};" in code
            assert "else { enqueue(plus_command); enqueue(minus_command); }" in code
        assert f"if (physical_on) enqueue({commands['off']});" in body
        assert f"if (!physical_on) enqueue({commands['on']});" in body
        assert f"enqueue({commands['on']});" in sync
        assert f"for (int i = 0; i < {substitutions.get('fan_sync_saturation_count', 6)}; i++) enqueue({sync_command});" in sync
        assert f"const bool anchor_out = {'true' if sync_direction == 'out' else 'false'};" in sync
        assert f"const int anchor_speed = {1 if sync_min else speed_count};" in sync
        assert f"if (!target_on) enqueue({commands['off']});" in sync

    if combined:
        aggregate = entity(config, "fan", "ventilation")
        assert aggregate["name"] == "Ventilation" and not aggregate["has_direction"]
        assert aggregate["speed_count"] == speed_count
        body = aggregate["on_state"][0]["then"][0]["if"]["then"][0]["lambda"].value
        assert "const bool target_on = id(ventilation).state;" in body
        assert body.index("id(fan433_batch_active) = true;") < body.index("auto call =")
        assert body.endswith("id(fan433_batch_active) = false;")
        calls = body.split("  auto call = ")[1:]
        assert len(calls) == len(fans)
        for (_, name, _), direction, call in zip(fans, (direction_in, direction_out), calls):
            assert call.startswith(f"id({name}).make_call();")
            assert "call.set_state(target_on);" in call and "call.set_speed(target_speed);" in call
            assert f"call.set_direction(fan::FanDirection::{direction});" in call

    transmitter = entity(config, "remote_transmitter", "radio_transmitter")
    assert transmitter["non_blocking"]
    complete = transmitter["on_complete"]["then"]
    pause_ms = int(substitutions.get("fan_command_pause", "100ms").removesuffix("ms"))
    assert next(item["delay"] for item in complete if "delay" in item).total_milliseconds == pause_ms
    assert "queue.erase(queue.begin());" in complete[1]["lambda"].value
    assert complete[3]["lambda"].value == "id(fan433_transmit_active) = false;"
    transmit = entity(config, "script", "fan433_transmit_queue")["then"][0]["if"]["then"][1]["remote_transmitter.transmit_raw"]
    assert str(transmit["transmitter_id"]) == "radio_transmitter"
    assert transmit["repeat"]["times"] == substitutions.get("fan_repeat_count", 4)
    assert transmit["repeat"]["wait_time"].total_microseconds == substitutions.get("fan_gap_us", 11900)
    assert f"const uint16_t short_us = {substitutions.get('fan_short_us', 400)};" in transmit["code"].value
    assert f"const uint16_t long_us = {substitutions.get('fan_long_us', 1200)};" in transmit["code"].value
    backend = "cc1101" if substitutions.get("test_radio_profile") == "esp32dev_cc1101" else "sx127x"
    assert "radio_transceiver" in ids(config, backend)
    for domain in ("fan", "button"):
        for item in config.get(domain, []):
            assert "${" not in str(item) and "<%" not in str(item)


def check(config, contract, substitutions):
    requirements = config["substitutions"]["esphome_requirements"]
    assert isinstance(requirements, list) and requirements
    required = max(cv.Version.parse(item["version"]) for item in requirements)
    assert config["esphome"]["min_version"] == str(required), "min_version must be the highest requirement"
    assert any(item["source"] == "esphome-lib.base" for item in requirements)
    uptime = entity(config, "sensor", "mcu_uptime")
    assert any(item["source"] == "sensor.device_class.uptime" for item in requirements) == (uptime["type"] == "timestamp")
    if "expected_min_version" in substitutions:
        assert config["esphome"]["min_version"] == substitutions["expected_min_version"]
    if contract == "versions":
        return
    if contract == "ct2":
        check_ct2(config, substitutions)
        return
    if contract == "strip4":
        check_strip4(config, substitutions)
        return
    if contract == "strip3x2":
        assert config["bk72xx"]["board"] == "cb2s"
        relays = ["socket_1_2", "socket_3_4", "socket_5_6", "relay_usb"]
        check_relay_group(config, "strip_power", relays, "power_status", "status_led")
        for relay, pin in zip(relays, (6, 7, 8, 26)):
            assert entity(config, "output", f"{relay}_power_output")["pin"]["number"] == pin
            assert entity(config, "switch", f"{relay}_power_relay")["restore_mode"] == "RESTORE_DEFAULT_OFF"
        assert entity(config, "output", "led_output")["pin"]["number"] == 10
        assert entity(config, "output", "led_output")["inverted"]
        button = next(s for s in config["binary_sensor"] if s["platform"] == "gpio")
        assert button["pin"]["number"] == 11 and button["pin"]["inverted"] and button["pin"]["mode"]["pullup"]
        assert str(button["on_press"][0]["then"][0]["script.execute"]["id"]) == "strip_power_toggle"
        assert config["web_server"]["version"] == 3
        return
    if contract == "relay-groups":
        check_relay_group(config, "first", ["r1"], "first_power_status", "first_led")
        check_relay_group(config, "second", ["r2"], "custom_status", "second_led")
        assert entity(config, "binary_sensor", "custom_status")["name"] == "Second Power"
        assert entity(config, "button", "second_cycle")["name"] == "Restart Second"
        return
    if contract == "ct16":
        check_ct16(config, substitutions)
        return
    if contract == "dehumidifier":
        check_dehumidifier(config)
        return
    if contract == "fan-power-sync":
        assert not check_fan_power(config, "first_fan", "first_power", "return true;")
        assert len(check_fan_power(config, "second_fan", "second_power", "return false;")) == 1
        first = entity(config, "fan", "first_fan")
        second = entity(config, "fan", "second_fan")
        assert first["name"] == "" and first["speed_count"] == 2 and not first["has_oscillating"]
        assert first["restore_mode"] == "RESTORE_DEFAULT_OFF"
        assert second["name"] == "Extract" and second["speed_count"] == 3 and second["has_oscillating"]
        assert second["restore_mode"] == "ALWAYS_OFF"
        return
    if contract == "rf-receiver":
        if not enabled(substitutions.get("receiver_enabled", True)):
            assert "remote_receiver" not in config
            return
        receivers = config["remote_receiver"]
        receiver = receivers[0] if isinstance(receivers, list) else receivers
        expected = 4000 if "esp32" in config else 16000
        if substitutions.get("receiver_buffer") == "8kb":
            expected = 8000
        assert receiver["buffer_size"] == expected
        return
    if contract == "ceiling-light-v2":
        chip = config["substitutions"]["chip"]
        is_cbu = chip == "cbu"
        platform = "bk72xx" if is_cbu else "ln882x"
        assert config[platform]["board"] == ("cbu" if is_cbu else "wl2h-u")
        assert ("ln882x" if is_cbu else "bk72xx") not in config
        channels = ("red", "green", "blue", "cold", "warm")
        expected_pins = (8, 7, 6, 26, 24) if is_cbu else (7, 10, 11, 12, 19)
        assert len(config["output"]) == 5
        for timer, (channel, pin) in enumerate(zip(channels, expected_pins)):
            output = entity(config, "output", f"out_{channel}")
            assert output["platform"] == ("libretiny_pwm" if is_cbu else "ln882h_pwm")
            assert output["pin"]["number"] == pin and not output["pin"]["inverted"]
            assert output["frequency"] == (5000 if is_cbu else 4000)
            assert output.get("max_power", 1) == 1
            assert ("timer" not in output) if is_cbu else (output["timer"] == timer)
        light = entity(config, "light", "main_light")
        assert light["platform"] == "rgbww" and light["name"] == ""
        assert light["constant_brightness"] and light["color_interlock"]
        for role, channel in zip(("red", "green", "blue", "cold_white", "warm_white"), channels):
            assert str(light[role]) == f"out_{channel}"
        has_ln882h_pwm = any(
            "ln882h_pwm" in source.get("components", [])
            for source in config.get("external_components", [])
        )
        assert has_ln882h_pwm != is_cbu, "Only the WL2H profile should load the external LN882H PWM driver"
        return
    if contract == "version-composition":
        sources = [item["source"] for item in requirements]
        assert sources.count("fixture.repeated") == 2
        assert "fixture.first" in sources and "fixture.second" in sources
        assert ("fixture.optional" in sources) == enabled(substitutions.get("test_optional", False))
        assert config["esphome"]["min_version"] == substitutions.get("expected_min_version", "2026.10.0")
        return
    if "esp32" in config:
        assert "<esp_ota_ops.h>" in config["esphome"]["includes"]
    if contract in ("offline", "offline-clock"):
        assert not {"wifi", "ethernet", "network", "api", "ota", "mdns"} & config.keys()
        assert "mcu_status" not in ids(config, "binary_sensor")
        assert not any(clock["platform"] == "homeassistant" for clock in config.get("time", []))
        assert not any("on_time_sync" in clock for clock in config.get("time", []))
        uptime = entity(config, "sensor", "mcu_uptime")
        if contract == "offline-clock":
            assert uptime["type"] == "timestamp"
            assert str(uptime["time_id"]) in ids(config, "time")
        else:
            assert uptime["type"] == "seconds" and "time_id" not in uptime
            assert uptime["device_class"] == "duration" and uptime["unit_of_measurement"] == "s"
        if "tuya" in config:
            assert str(config["tuya"]["time_id"]) == "ha_time"
            assert "ha_time" in ids(config, "time")
        if "channel1_power_output" in ids(config, "output"):
            assert "channel1_control_on" in ids(config, "script")
    elif contract == "networking-single":
        assert ("wifi" in config) != ("ethernet" in config)
        ethernet = "ethernet" in config
        api_enabled = enabled(substitutions.get("test_api", True))
        assert config["esphome"]["min_version"] == "2026.10.0"
        info = next(sensor for sensor in config["text_sensor"] if sensor["platform"] == ("ethernet_info" if ethernet else "wifi_info"))
        assert str(info["mac_address"]["id"]) == "mcu_mac_address"
        ip_id = "mcu_ip_address" if ethernet else "mcu_ip"
        assert str(info["ip_address"]["id"]) == ip_id
        assert ("api" in config) == api_enabled
        assert ("ha_time" in ids(config, "time")) == api_enabled
        assert entity(config, "sensor", "mcu_uptime")["type"] == ("timestamp" if api_enabled else "seconds")
        assert ("ota" in config) == enabled(substitutions.get("test_ota", True))
        assert config["mdns"]["disabled"] != enabled(substitutions.get("test_mdns", True))
        if ethernet and "test_ethernet_on_boot" in substitutions:
            assert config["ethernet"]["enable_on_boot"] == enabled(substitutions["test_ethernet_on_boot"])
    elif contract in ("networking", "networking-appliance"):
        interfaces = config["substitutions"]["test_interfaces"]
        assert [item["interface"] for item in config["network"]["priority"]] == interfaces
        assert {"wifi", "ethernet"} <= config.keys()
        assert config["esphome"]["min_version"] == "2026.10.0"
        api_enabled = enabled(substitutions.get("test_api", True))
        assert ("api" in config) == api_enabled
        if api_enabled:
            assert str(config["api"]["id"]) == "hapi"
            assert config["api"]["reboot_timeout"].total_milliseconds == 0
            assert substitutions.get("test_clock_id", "ha_time") in ids(config, "time")
        else:
            assert not any(clock["platform"] == "homeassistant" for clock in config.get("time", []))
        assert ("ota" in config) == enabled(substitutions.get("test_ota", True))
        assert config["mdns"]["disabled"] != enabled(substitutions.get("test_mdns", True))
        assert config["wifi"]["enable_on_boot"] == enabled(substitutions.get("test_wifi_on_boot", True))
        assert config["ethernet"]["enable_on_boot"] == enabled(substitutions.get("test_ethernet_on_boot", True))
        assert config["wifi"]["reboot_timeout"].total_milliseconds == 0
        assert "mcu_status" in ids(config, "binary_sensor")
        uptime = entity(config, "sensor", "mcu_uptime")
        assert uptime["type"] == ("timestamp" if api_enabled else "seconds")
        diagnostic_ids = set()
        for sensor in config["text_sensor"]:
            if sensor["platform"] in ("wifi_info", "ethernet_info"):
                prefix = "wifi" if sensor["platform"] == "wifi_info" else "ethernet"
                for key in ("ip_address", "mac_address"):
                    name = str(sensor[key]["id"])
                    assert name == f"mcu_{prefix}_{key}" and name not in diagnostic_ids
                    diagnostic_ids.add(name)
        assert len(diagnostic_ids) == 4
        if contract == "networking-appliance":
            if substitutions.get("test_appliance") == "heltec-hri-485x":
                assert config["ethernet"]["type"] == "RTL8201"
                assert config["ethernet"]["clk"]["pin"] == 17
                if api_enabled:
                    assert "on_client_connected" in config["api"]
            else:
                assert config["ethernet"]["type"] == "W5500"
                assert config["ethernet"]["clk_pin"] == 15
                clock = entity(config, "time", substitutions.get("test_clock_id", "ha_time"))
                action = clock["on_time_sync"][0]["then"][0]["pcf85063.write_time"]
                assert str(action["id"]) == "waveshare_8di8ro_rtc"
    elif contract == "fan433":
        check_fan433(config, substitutions)
    elif contract == "esp8266-relay-pin":
        pin = entity(config, "output", "channel1_power_output")["pin"]
        assert pin["number"] == 4 and pin["mode"]["output"]
        assert not pin["inverted"] and not pin["allow_other_uses"]
        assert not {"drive_strength", "ignore_strapping_warning", "ignore_pin_validation_error"} & pin.keys()
    elif contract == "pins":
        platform = config["substitutions"]["firmware_platform"]
        assert platform == CORE.target_platform
        esp32 = platform == "esp32"
        output = entity(config, "output", "pin_test_output")["pin"]
        input_pin = entity(config, "binary_sensor", "pin_test_input")["pin"]
        input_copy = entity(config, "binary_sensor", "pin_test_input_copy")["pin"]
        assert output["inverted"] and not output["allow_other_uses"]
        assert output["mode"]["output"] and output["mode"]["open_drain"]
        assert not output["mode"]["input"] and not output["mode"]["pullup"]
        assert input_pin["number"] == input_copy["number"]
        for pin in (input_pin, input_copy):
            assert pin["mode"]["input"] and pin["mode"]["pullup"]
            assert pin["allow_other_uses"] and not pin["inverted"]
            assert not pin["mode"]["output"] and not pin["mode"]["pulldown"]
        special = {"drive_strength", "ignore_strapping_warning", "ignore_pin_validation_error"}
        for pin in (output, input_pin, input_copy):
            assert (special & pin.keys()) == (special if esp32 else set())
        if esp32:
            assert output["drive_strength"] == 40
            assert input_pin["drive_strength"] == 20
            assert not output["ignore_pin_validation_error"]
            assert output["ignore_strapping_warning"] == enabled(substitutions.get("ignore_strapping", False))
        number = config["substitutions"]["number_pin"]
        assert set(number) == ({"number", "ignore_strapping_warning"} if esp32 else {"number"})
        if esp32:
            assert enabled(number["ignore_strapping_warning"]) == enabled(substitutions.get("ignore_strapping", False))
        uart = entity(config, "uart", "pin_test_uart")
        token = path_context.set(["substitutions", "number_pin"])
        try:
            assert pins.internal_gpio_output_pin_number(number) == uart["tx_pin"]["number"]
        finally:
            path_context.reset(token)
    elif contract == "disabled-basic":
        assert "sbr4_power_output" in ids(config, "output")
        assert "sbr4_power_state" not in ids(config, "binary_sensor")
        assert "sbr4_primary_toggle" not in ids(config, "script")
        assert "sbr4_magic_switch_dnd" not in ids(config, "switch")
        assert "magic_switch" not in config
    elif contract == "enabled-basic":
        assert "sbr4_primary_toggle" in ids(config, "script")
        assert "sbr4_magic_switch_dnd" in ids(config, "switch")
        magic = entity(config, "magic_switch", "sbr4_magic_switch")
        assert magic["pin"]["number"] == 5
        action = magic["on_switch"]["then"][0]["if"]
        assert str(action["condition"]["switch.is_off"]["id"]) == "sbr4_magic_switch_dnd"
        assert str(action["then"][0]["script.execute"]["id"]) == "sbr4_primary_toggle"
        hook = entity(config, "script", "sbr4_after_power_change")
        mask = next(item["magic_switch.mask"] for item in hook["then"] if "magic_switch.mask" in item)
        assert str(mask["id"]) == "sbr4_magic_switch"
        assert mask["duration"].total_milliseconds == 500
    elif contract == "two-relay":
        first = enabled(substitutions.get("first_enabled", False))
        second = enabled(substitutions.get("second_enabled", True))
        assert {"relay_1_power_output", "relay_2_power_output"} <= ids(config, "output")
        for index, active in ((1, first), (2, second)):
            prefix = f"relay_{index}"
            assert (f"{prefix}_power_state" in ids(config, "binary_sensor")) == active
            assert (f"{prefix}_power_on" in ids(config, "script")) == active
        assert ("master_switch" in ids(config, "binary_sensor")) == (first or second)
        if first or second:
            action = entity(config, "binary_sensor", "master_switch")["on_click"][0]["then"][0]["if"]
            prefixes = [f"relay_{i}" for i, active in ((1, first), (2, second)) if active]
            assert [str(item["binary_sensor.is_on"]["id"]) for item in action["condition"]["or"]] == [f"{p}_power_state" for p in prefixes]
            for branch, command in (("then", "off"), ("else", "on")):
                assert [str(item["script.execute"]["id"]) for item in action[branch]] == [f"{p}_power_{command}" for p in prefixes]
    elif contract == "radio-frequency":
        assert entity(config, "sx127x", "radio_transceiver")["frequency"] == 868350000
    elif contract == "earu":
        temperature = entity(config, "sensor", "temperature")
        assert temperature["update_interval"].total_milliseconds == 1000
        assert temperature["filters"][1]["throttle_average"].total_milliseconds == 10000
        meter = next(item for item in config["sensor"] if item["platform"] == "bl0942")
        assert meter["update_interval"].total_milliseconds == 1000
        assert meter["energy"]["unit_of_measurement"] == "kWh"
        assert config["uart"][0]["baud_rate"] == 4800
    elif contract.startswith("wifi-"):
        network = config["wifi"]["networks"][0]
        expected = {
            "wifi-explicit": ("test-network", "test-password"),
            "wifi-open": ("open-network", ""),
            "wifi-ssid": ("explicit-network", "fallback-password"),
            "wifi-password": ("fallback-network", "explicit-password"),
        }[contract]
        assert (network["ssid"], network["password"]) == expected
    elif contract == "inherited-logger":
        assert config["logger"]["level"] == "WARN"
        assert config["logger"]["baud_rate"] == 0
    elif contract == "serial-bridge":
        assert config["esp8266"]["board"] == "esp07"
        assert config["logger"]["baud_rate"] == 0
        assert config["api"]["reboot_timeout"].total_milliseconds == 0
        assert config["wifi"]["reboot_timeout"].total_milliseconds == 0
        assert any(item["platform"] == "esphome" for item in config["ota"])
        assert entity(config, "time", "ha_time")["platform"] == "homeassistant"
        uptime = entity(config, "sensor", "mcu_uptime")
        assert uptime["type"] == "timestamp"
        assert uptime["device_class"] == "uptime"
        assert str(uptime["time_id"]) == "ha_time"
        uart = entity(config, "uart", "serial_uart")
        assert (uart["tx_pin"]["number"], uart["rx_pin"]["number"]) == (1, 3)
        assert uart["baud_rate"] == int(substitutions.get("uart_baud_rate", 115200))
        assert (uart["data_bits"], uart["parity"], uart["stop_bits"]) == (8, "NONE", 1)
        server = entity(config, "uart_tcp", "serial_bridge")
        assert server["role"] == "server"
        assert "stream_server" not in config and "external_components" not in config
        assert config["esp8266"]["toolchain"] == "arduino"
        assert str(server["uart_id"]) == "serial_uart"
        assert server["port"] == int(substitutions.get("tcp_port", 6638))
    elif contract.startswith("serial-logger-"):
        expected = {
            "serial-logger-esp07": (0, "UART0"),
            "serial-logger-cn105": (0, "UART0"),
            "serial-logger-esp12ef": (0, "UART0"),
            "serial-logger-beken": (115200, "DEFAULT"),
            "serial-logger-hri4853": (0, "UART0"),
        }[contract]
        assert (config["logger"]["baud_rate"], config["logger"]["hardware_uart"]) == expected
        if contract == "serial-logger-cn105":
            hub = config["mitsubishi_cn105"]
            assert str(hub["id"]) == "hp_protocol"
            assert str(hub["uart_id"]) == "HP_UART"
            assert hub["update_interval"].total_milliseconds == 2000
            assert hub["telemetry_request_min_interval"].total_milliseconds == 2000
            climate = entity(config, "climate", "hp")
            assert climate["name"] == "Heat Pump"
            assert str(climate["mitsubishi_cn105_id"]) == "hp_protocol"
            remote = entity(config, "sensor", "remote_temperature")
            action = remote["on_value"][0]["then"][1]["mitsubishi_cn105.set_remote_temperature"]
            assert str(action["id"]) == "hp_protocol"
            fallback = config["interval"][0]["then"][0]["if"]["then"][1]
            assert str(fallback["mitsubishi_cn105.clear_remote_temperature"]["id"]) == "hp_protocol"
        if contract == "serial-logger-beken":
            uart = entity(config, "uart", "tuya_uart")
            assert uart["tx_pin"]["number"] == 11
            assert uart["rx_pin"]["number"] == 10
    else:
        raise AssertionError(f"Unknown contract: {contract}")


if __name__ == "__main__":
    CORE.config_path = Path(sys.argv[1]).resolve()
    substitutions = json.loads(sys.argv[3])
    config = read_config({key: str(value) for key, value in substitutions.items()})
    assert config is not None, "ESPHome configuration failed"
    check(config, sys.argv[2], substitutions)
    print(f"PASS resolved contract: {sys.argv[2]}")
