"""Keep LibreTiny's Beken OTA encryption independent of the build host."""

from pathlib import Path

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.core import CORE
from esphome.helpers import copy_file_if_changed

CODEOWNERS = ["@ngorchilov"]
DEPENDENCIES = ["bk72xx"]
CONFIG_SCHEMA = cv.Schema({})


async def to_code(config):
    filename = "bk72xx_ota_packaging.py"
    copy_file_if_changed(
        Path(__file__).with_name(filename + ".script"),
        CORE.relative_build_path(filename),
    )
    cg.add_platformio_option("extra_scripts", ["post:" + filename])
