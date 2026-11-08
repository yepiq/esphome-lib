from esphome import automation
import esphome.codegen as cg
from esphome.components import fan
import esphome.config_validation as cv
from esphome.const import CONF_SPEED_COUNT, CONF_TRIGGER_ID

DEPENDENCIES = ["fan"]
ns = cg.esphome_ns.namespace("command_fan")
CommandFan = ns.class_("CommandFan", cg.Component, fan.Fan)
FanCall = fan.fan_ns.class_("FanCall")
CommandTrigger = ns.class_("CommandTrigger", automation.Trigger.template(FanCall.operator("ref").operator("const")))

CONFIG_SCHEMA = fan.fan_schema(CommandFan).extend({
    cv.Required(CONF_SPEED_COUNT): cv.int_range(min=1),
    cv.Optional("has_oscillating", default=False): cv.boolean,
    cv.Optional("on_control"): automation.validate_automation({
        cv.GenerateID(CONF_TRIGGER_ID): cv.declare_id(CommandTrigger),
    }),
}).extend(cv.COMPONENT_SCHEMA)

async def to_code(config):
    var = await fan.new_fan(config)
    await cg.register_component(var, config)
    cg.add(var.set_speed_count(config[CONF_SPEED_COUNT]))
    cg.add(var.set_has_oscillating(config["has_oscillating"]))
    for conf in config.get("on_control", []):
        trigger = cg.new_Pvariable(conf[CONF_TRIGGER_ID], var)
        await automation.build_automation(trigger, [(FanCall.operator("ref").operator("const"), "x")], conf)
