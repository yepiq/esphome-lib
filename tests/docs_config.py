"""Validate complete consumer README examples against checked-out packages, config only."""

import json
import os
from pathlib import Path
import re
import sys
import tempfile

import yaml

from validate import DUMMY_SECRETS, ROOT, run, snapshot

DOCS = [
    Path("README.md"), Path("devices/README.md"), Path("packages/README.md"),
    Path("packages/modules/README.md"), Path("packages/modules/networking/README.md"),
    *sorted(path.relative_to(ROOT) for path in (ROOT / "packages/appliances").glob("*/README.md")),
]
URL = "https://github.com/yepiq/esphome-lib"


def field(node, name):
    if isinstance(node, yaml.MappingNode):
        return next((value for key, value in node.value if key.value == name), None)
    return None


def complete_examples(text):
    # YAML nodes retain ESPHome's custom tags without evaluating includes or secrets.
    for index, match in enumerate(re.finditer(r"^```yaml\s*\n(.*?)^```\s*$", text,
                                             re.MULTILINE | re.DOTALL), 1):
        node = yaml.compose(match.group(1))
        if field(node, "packages") is not None and field(field(node, "substitutions"), "name") is not None:
            yield index, node


def include_node(path, variables=None):
    scalar = lambda value: yaml.ScalarNode("tag:yaml.org,2002:str", str(value))
    if variables is None:
        return yaml.ScalarNode("!include", str(path))
    return yaml.MappingNode("!include", [(scalar("file"), scalar(path)),
                                         (scalar("vars"), variables)])


def local_packages(node, work):
    """Mirror only this repository's remote entries; preserve vars and all other YAML tags."""
    work = work.resolve()
    packages = field(node, "packages")

    def expand(entry):
        url = field(entry, "url")
        if url is None or url.value != URL:
            if entry.tag == "!include":
                path = entry if isinstance(entry, yaml.ScalarNode) else field(entry, "file")
                prefix = "esphome-lib/"
                if path.value.startswith(prefix):
                    return [include_node(work / path.value[len(prefix):], field(entry, "vars"))]
                if Path(path.value).parts[0] in ("devices", "packages", "kickstart"):
                    return [include_node(work / path.value, field(entry, "vars"))]
            return [entry]
        files = field(entry, "files")
        if not isinstance(files, yaml.SequenceNode):
            raise ValueError("Remote example must provide a files list")
        result = []
        for item in files.value:
            path = item if isinstance(item, yaml.ScalarNode) else field(item, "path")
            target = (work / path.value).resolve()
            if not target.is_relative_to(work) or not target.is_file():
                raise ValueError(f"Example includes missing/non-repository path: {path.value}")
            result.append(include_node(target, field(item, "vars")))
        return result

    if isinstance(packages, yaml.SequenceNode):
        packages.value = [item for entry in packages.value for item in expand(entry)]
    elif isinstance(packages, yaml.MappingNode):
        # ESPHome accepts an inline package containing its own package list.
        packages.value = [(key, yaml.MappingNode("tag:yaml.org,2002:map", [
            (yaml.ScalarNode("tag:yaml.org,2002:str", "packages"),
             yaml.SequenceNode("tag:yaml.org,2002:seq", expand(entry)))
        ])) for key, entry in packages.value]
    else:
        raise ValueError("Unsupported packages shape in documentation example")
    return node


def main():
    root = Path(tempfile.mkdtemp(prefix="esphome-lib-docs-"))
    work = root / "work"
    snapshot(work)
    examples = work / "doc-examples"
    examples.mkdir()
    (examples / "secrets.yaml").write_text(yaml.safe_dump(DUMMY_SECRETS))
    logs = root / "logs"
    logs.mkdir()
    env = os.environ.copy()
    env["ESPHOME_LIB_SOURCE"] = str(work / "components")
    env.setdefault("ESPHOME_DATA_DIR", str(root / "cache"))
    env["NO_COLOR"] = "1"
    results = []
    print(f"Artifacts: {root}", flush=True)
    for document in DOCS:
        for index, node in complete_examples((ROOT / document).read_text()):
            name = str(document.with_suffix("")).replace("/", "-") + f"-{index}"
            path = examples / f"{name}.yaml"
            path.write_text(yaml.serialize(local_packages(node, work)))
            code, output = run([sys.executable, "-m", "esphome", "config", path.name],
                               examples, env, 180)
            (logs / f"{name}.log").write_text(output)
            status = "PASS" if code == 0 else "FAIL"
            print(f"{status} {document} YAML block {index}", flush=True)
            results.append({"document": str(document), "block": index, "status": status})
            if code:
                print(output[-6000:], flush=True)
    (root / "results.json").write_text(json.dumps(results, indent=2) + "\n")
    print(f"{sum(item['status'] == 'PASS' for item in results)}/{len(results)} examples passed")
    return 0 if results and all(item["status"] == "PASS" for item in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
