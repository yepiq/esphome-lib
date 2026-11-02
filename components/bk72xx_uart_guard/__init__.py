"""Interrupt-safe LibreTiny Serial reads on Beken's ARM968 core."""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.config_helpers import filter_source_files_from_defines
from esphome.core import CORE

CODEOWNERS = ["@ngorchilov"]
DEPENDENCIES = ["bk72xx"]

CONFIG_SCHEMA = cv.Schema({})

FILTER_SOURCE_FILES = filter_source_files_from_defines(
    {
        "bk72xx_uart_guard.cpp": "USE_BK72XX_UART_GUARD",
        "bk72xx_uart_guard.h": "USE_BK72XX_UART_GUARD",
        "uart_overflow_sensor.cpp": "USE_BK72XX_UART_OVERFLOW_SENSOR",
        "uart_overflow_sensor.h": "USE_BK72XX_UART_OVERFLOW_SENSOR",
    }
)


async def to_code(config):
    # CORE.config includes the complete, merged package configuration.
    if CORE.config.get("uart"):
        cg.add_define("USE_BK72XX_UART_GUARD")
        cg.add_build_flag("-Wl,--wrap=_ZN11SerialClass4readEv")
