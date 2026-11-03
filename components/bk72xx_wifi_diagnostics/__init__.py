"""Temporary receive-path diagnostics for BK7231N / LibreTiny 1.13."""

import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import libretiny, sensor, text_sensor
from esphome.components.libretiny.const import FAMILY_BK7231N
from esphome.const import CONF_ID, ENTITY_CATEGORY_DIAGNOSTIC, STATE_CLASS_TOTAL_INCREASING

CODEOWNERS = ["@ngorchilov"]
DEPENDENCIES = ["bk72xx", "wifi"]
AUTO_LOAD = ["sensor", "text_sensor"]
ns = cg.esphome_ns.namespace("bk72xx_wifi_diagnostics")
WiFiDiagnostics = ns.class_("WiFiDiagnostics", cg.PollingComponent)
COUNTERS = ("unicast_ipv4", "group_ipv4", "unicast_arp", "group_arp", "unicast_eapol", "group_eapol")

CONFIG_SCHEMA = cv.Schema(
    {
        cv.GenerateID(): cv.declare_id(WiFiDiagnostics),
        **{cv.Required(key): sensor.sensor_schema(
            accuracy_decimals=0,
            unit_of_measurement="packets",
            state_class=STATE_CLASS_TOTAL_INCREASING,
            entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
        ) for key in COUNTERS},
        cv.Required("event_history"): text_sensor.text_sensor_schema(entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
        cv.Required("rx_snapshot"): text_sensor.text_sensor_schema(entity_category=ENTITY_CATEGORY_DIAGNOSTIC),
    }
).extend(cv.polling_component_schema("10s"))


def final_validate(config):
    if libretiny.get_libretiny_family() != FAMILY_BK7231N:
        raise cv.Invalid("bk72xx_wifi_diagnostics currently supports BK7231N only")
    return config


FINAL_VALIDATE_SCHEMA = final_validate


async def to_code(config):
    var = cg.new_Pvariable(config[CONF_ID])
    await cg.register_component(var, config)
    for i, key in enumerate(COUNTERS):
        entity = await sensor.new_sensor(config[key])
        cg.add(var.set_counter(i, entity))
    for key in ("event_history", "rx_snapshot"):
        entity = await text_sensor.new_text_sensor(config[key])
        cg.add(getattr(var, f"set_{key}")(entity))
    cg.add_build_flag("-Wl,--wrap=ethernetif_input")
