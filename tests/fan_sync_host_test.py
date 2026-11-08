"""Execute resolved fan actions and actual MCU callbacks against deterministic host doubles."""

import os
from pathlib import Path
import subprocess
import tempfile

import yaml
from esphome.config import read_config
from esphome.core import CORE

from validate import DUMMY_SECRETS, ROOT, snapshot


def condition(node):
    if "lambda" in node:
        return f"([&]() -> bool {{ {node['lambda'].value} }})()"
    for state in ("on", "off"):
        if f"switch.is_{state}" in node:
            return ("!" if state == "off" else "") + f"id({node[f'switch.is_{state}']['id']}).state"
    raise AssertionError(f"Unsupported test condition: {node}")


def actions(nodes):
    result = []
    for node in nodes:
        if "if" in node:
            branch = node["if"]
            result.append(f"if ({condition(branch['condition'])}) {{ {actions(branch['then'])} }} "
                          f"else {{ {actions(branch.get('else', []))} }}")
        elif "lambda" in node:
            result.append(f"[&]() {{ {node['lambda'].value} }}();")
        else:
            for state in ("on", "off"):
                if f"switch.turn_{state}" in node:
                    result.append(f"id({node[f'switch.turn_{state}']['id']}).turn_{state}();")
                    break
            else:
                raise AssertionError(f"Unsupported test action: {node}")
    return "\n".join(result)


def main():
    with tempfile.TemporaryDirectory(prefix="esphome-fan-host-") as temporary:
        work = Path(temporary) / "work"
        snapshot(work)
        (work / "devices/secrets.yaml").write_text(yaml.safe_dump(DUMMY_SECRETS))
        os.environ["ESPHOME_LIB_SOURCE"] = str(work / "components")
        os.environ["ESPHOME_DATA_DIR"] = str(Path(temporary) / "cache")
        source = (ROOT / "tests/fan_sync_host_test.cpp").read_text()
        for device, prefix, datapoints in (
            ("pro-breeze-dehumidifier", "pb", (1, 6, 8)),
            ("jummico-dehumidifier", "jummico", (1, 4)),
        ):
            CORE.reset()
            CORE.config_path = work / f"devices/{device}.yaml"
            config = read_config({})
            assert config is not None
            fan = next(f for f in config["fan"] if str(f["id"]) == f"{prefix}_fan")
            source = source.replace(f"{prefix.upper()}_COMMAND_BODY", actions(fan["on_state"][0]["then"]))
            if prefix == "pb":
                source = source.replace("PB_CONTROL_BODY", actions(fan["on_control"][0]["then"]))
            for dp in datapoints:
                callback = next(c for c in config["tuya"]["on_datapoint_update"] if c["sensor_datapoint"] == dp)
                source = source.replace(f"{prefix.upper()}_DP{dp}_BODY", actions(callback["then"]))
        binary = Path(temporary) / "fan-sync-test"
        subprocess.run([os.environ.get("CXX", "clang++"), "-std=c++17",
                        "-fsanitize=address,undefined", "-fno-omit-frame-pointer",
                        "-x", "c++", "-", "-o", str(binary)],
                       input=source, text=True, check=True)
        subprocess.run([str(binary)], check=True)


if __name__ == "__main__":
    main()
