"""Run config-only regressions against an isolated working-tree snapshot."""

import argparse
from collections import Counter
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

import yaml

ROOT = Path(__file__).resolve().parents[1]
DUMMY_SECRETS = {
    "wifi_ssid": "test-network",
    "wifi_password": "test-password",
    "tuya_garage_opener_ble_command": 0xA1B2C3,
}


def tracked_files():
    result = subprocess.run(["git", "ls-files", "-z"], cwd=ROOT,
                            text=True, capture_output=True, check=True)
    return [Path(name) for name in result.stdout.split("\0") if name and (ROOT / name).is_file()]


def snapshot(destination):
    # Include new fixtures/packages too, but never copy credentials or build/cache directories.
    for directory in ("devices", "kickstart", "packages", "components", "tests", "data-models"):
        shutil.copytree(ROOT / directory, destination / directory,
                        ignore=shutil.ignore_patterns(".*", "secrets.yaml", "__pycache__", "*.pyc"))


def unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def check_models(files):
    models = [path for path in files if path.parts[0] == "data-models" and path.suffix == ".json"]
    for path in models:
        try:
            data = json.loads((ROOT / path).read_text(), object_pairs_hook=unique_pairs)
            if path.parent.name == "things-data-model":
                assert data["modelId"] and isinstance(data["services"], list)
                for service in data["services"]:
                    ids = [prop["abilityId"] for prop in service["properties"]]
                    assert len(ids) == len(set(ids)), "Duplicate datapoint ID"
        except (ValueError, KeyError, AssertionError) as error:
            raise ValueError(f"{path}: {error}") from error
    print(f"PASS {len(models)} JSON models", flush=True)


def run(command, cwd, env, timeout):
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                                text=True, timeout=timeout)
        return result.returncode, result.stderr + result.stdout
    except subprocess.TimeoutExpired:
        return 124, f"TIMEOUT after {timeout}s: {command}"


def classify(code, output, case):
    expected = case.get("known_failure", case.get("reject"))
    if expected:
        if code == 0:
            return "XPASS" if "known_failure" in case else "FAIL"
        if code != 124 and expected in output and "Failed config" in output:
            return "XFAIL" if "known_failure" in case else "REJECTED"
        return "FAIL"
    return "PASS" if code == 0 else "FAIL"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("targets", nargs="*", help="Case IDs or device/kickstart paths")
    parser.add_argument("--all", action="store_true", help="Also validate every tracked device/kickstart")
    parser.add_argument("--timeout", type=int, default=180, help="Seconds per subprocess")
    args = parser.parse_args()
    files = tracked_files()
    check_models(files)
    cases = yaml.safe_load((ROOT / "tests/cases.yaml").read_text())["cases"]
    if args.targets:
        by_id = {case["id"]: case for case in cases}
        selected = []
        for target in args.targets:
            if target in by_id:
                selected.append(by_id[target])
            elif Path(target) in files and Path(target).parts[0] in ("devices", "kickstart") and target.endswith(".yaml"):
                selected.append({"id": Path(target).stem, "file": target})
            else:
                parser.error(f"Unknown case or tracked firmware: {target}")
        cases = selected
    if args.all:
        covered = {case["file"] for case in cases if not case.get("substitutions")}
        cases += [{"id": path.stem, "file": str(path)} for path in files
                  if path.parts[0] in ("devices", "kickstart") and len(path.parts) == 2
                  and path.suffix == ".yaml" and str(path) not in covered]

    root = Path(tempfile.mkdtemp(prefix="esphome-lib-validation-"))
    work = root / "work"
    snapshot(work)
    logs = root / "logs"
    logs.mkdir()
    env = os.environ.copy()
    env["ESPHOME_LIB_SOURCE"] = str(work / "components")
    # A caller can opt into an existing cache; the default does not touch checkout caches.
    env.setdefault("ESPHOME_DATA_DIR", str(root / "cache"))
    env["NO_COLOR"] = "1"
    results = []
    print(f"Artifacts: {root}", flush=True)
    for case in cases:
        path = work / case["file"]
        secret_file = path.parent / "secrets.yaml"
        # Give each case exactly its declared credentials, including partial-secret tests.
        for old_secret in work.rglob("secrets.yaml"):
            old_secret.unlink()
        secrets = case.get("secrets", True)
        if secrets is not False:
            secret_file.write_text(yaml.safe_dump(DUMMY_SECRETS if secrets is True else secrets))
        command = [sys.executable, "-m", "esphome"]
        for key, value in case.get("substitutions", {}).items():
            command += ["-s", key, str(value)]
        command += ["config", path.name]
        code, output = run(command, path.parent, env, args.timeout)
        status = classify(code, output, case)
        if status == "PASS" and case.get("local_components"):
            command = [sys.executable, str(work / "tests/check_component_sources.py"),
                       str(path), *case["local_components"]]
            code, provenance = run(command, path.parent, env, args.timeout)
            output += "\nComponent provenance:\n" + provenance
            if code:
                status = "FAIL"
        if status == "PASS":
            command = [sys.executable, str(work / "tests/check_contracts.py"), str(path),
                       case.get("contract", "versions"), json.dumps(case.get("substitutions", {}))]
            code, contract = run(command, path.parent, env, args.timeout)
            output += "\nResolved contract:\n" + contract
            if code:
                status = "FAIL"
        (logs / f"{case['id']}.log").write_text(output)
        results.append({"id": case["id"], "file": case["file"], "status": status,
                        "reason": case.get("reason", "")})
        print(f"{status} {case['id']}" + (f" ({case['reason']})" if case.get("reason") else ""), flush=True)
        if status in ("FAIL", "XPASS"):
            post_config_check = "Component provenance:" in output or "Resolved contract:" in output
            print(output[-5000:] if post_config_check else output[:5000], flush=True)
    (root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(dict(Counter(result["status"] for result in results)), flush=True)
    return int(any(result["status"] in ("FAIL", "XPASS") for result in results))


if __name__ == "__main__":
    sys.exit(main())
