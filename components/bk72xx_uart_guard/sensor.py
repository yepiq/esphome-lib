import esphome.codegen as cg
import esphome.config_validation as cv
from esphome.components import sensor, uart
from esphome.const import ENTITY_CATEGORY_DIAGNOSTIC, STATE_CLASS_TOTAL_INCREASING

DEPENDENCIES = ["bk72xx_uart_guard", "uart"]

ns = cg.esphome_ns.namespace("bk72xx_uart_guard")
UARTOverflowSensor = ns.class_(
    "UARTOverflowSensor", sensor.Sensor, cg.PollingComponent, uart.UARTDevice
)

CONFIG_SCHEMA = (
    sensor.sensor_schema(
        UARTOverflowSensor,
        accuracy_decimals=0,
        unit_of_measurement="events",
        state_class=STATE_CLASS_TOTAL_INCREASING,
        entity_category=ENTITY_CATEGORY_DIAGNOSTIC,
    )
    .extend(cv.polling_component_schema("1s"))
    .extend(uart.UART_DEVICE_SCHEMA)
)

FINAL_VALIDATE_SCHEMA = uart.final_validate_device_schema(
    "bk72xx_uart_guard", require_rx=True
)


async def to_code(config):
    cg.add_define("USE_BK72XX_UART_OVERFLOW_SENSOR")
    cg.add_build_flag("-Wl,--wrap=uart_read_byte")
    var = await sensor.new_sensor(config)
    await cg.register_component(var, config)
    await uart.register_uart_device(var, config)
