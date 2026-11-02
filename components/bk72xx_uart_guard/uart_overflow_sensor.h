#pragma once

#include "esphome/core/defines.h"
#ifdef USE_BK72XX_UART_OVERFLOW_SENSOR
#include "esphome/core/component.h"
#include "esphome/core/preferences.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/uart/uart.h"

namespace esphome::bk72xx_uart_guard {

class UARTOverflowSensor : public sensor::Sensor, public PollingComponent, public uart::UARTDevice {
 public:
  void setup() override;
  void dump_config() override;
  void update() override;
  void on_shutdown() override;
  float get_setup_priority() const override { return setup_priority::DATA; }

 protected:
  ESPPreferenceObject preference_;
  uint32_t restored_total_{0};
  uint32_t saved_total_{0};
  uint32_t published_total_{0};
  int8_t port_{-1};
};

}  // namespace esphome::bk72xx_uart_guard
#endif
