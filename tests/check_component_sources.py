"""Check actual Python module provenance after ESPHome configuration loading."""

import os
from pathlib import Path
import sys

from esphome.config import read_config
from esphome.core import CORE
from esphome.yaml_util import load_yaml


def main():
    config_path = Path(sys.argv[1]).resolve()
    component_root = Path(os.environ["ESPHOME_LIB_SOURCE"]).resolve()
    # Check the consumer default as well, without fetching any remote code.
    source_file = component_root.parent / "packages/component-source.yaml"
    selected = os.environ.pop("ESPHOME_LIB_SOURCE")
    try:
        assert load_yaml(source_file) == "github://yepiq/esphome-lib"
    finally:
        os.environ["ESPHOME_LIB_SOURCE"] = selected
    CORE.config_path = config_path
    assert read_config({}) is not None, "ESPHome config failed"
    for component in sys.argv[2:]:
        prefix = f"esphome.components.{component}"
        modules = [module for name, module in sys.modules.items()
                   if name == prefix or name.startswith(prefix + ".")]
        assert modules, f"{component} was not imported by ESPHome"
        for module in modules:
            path = Path(module.__file__).resolve()
            assert path.is_relative_to(component_root / component), path
            print(f"LOCAL {component}: {path}")


if __name__ == "__main__":
    main()
