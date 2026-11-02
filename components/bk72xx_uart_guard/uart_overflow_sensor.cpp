#include "uart_overflow_sensor.h"

#ifdef USE_BK72XX_UART_OVERFLOW_SENSOR
#include "bk72xx_uart_guard.h"
#include "esphome/components/uart/uart_component_libretiny.h"
#include "esphome/core/helpers.h"
#include "esphome/core/log.h"
#include <Arduino.h>
#include <Serial.h>

namespace esphome::bk72xx_uart_guard {
static const char *const TAG = "bk72xx_uart_guard";

// Count from UART startup, before sensor setup; never publish or save inside the ISR.
static volatile uint32_t overflow_count[2]{};
static UARTOverflowSensor *monitors[2]{};

void UARTOverflowSensor::setup() {
  auto *bus = static_cast<uart::LibreTinyUARTComponent *>(this->parent_);
  const int port = bus->get_hw_serial_number() - 1;
  if (port < 0 || port >= 2 || monitors[port] != nullptr) {
    ESP_LOGE(TAG, "Overflow monitoring requires a unique hardware UART1 or UART2");
    this->mark_failed();
    return;
  }
  this->port_ = port;
  monitors[port] = this;
  // Stable per-port key: firmware rebuilds and sensor renames must retain the total.
  const uint32_t key = fnv1_hash("bk72xx_uart_guard.rx_overflow.v1") ^ uint32_t(port);
  this->preference_ = global_preferences->make_preference<uint32_t>(key);
  this->preference_.load(&this->restored_total_);
  this->saved_total_ = this->restored_total_;
  this->update();
}

void UARTOverflowSensor::update() {
  if (this->port_ < 0)
    return;
  const uint32_t saved = save_and_mask_irq_fiq();
  const uint32_t received_overflows = overflow_count[this->port_];
  restore_irq_fiq(saved);
  const uint32_t total = this->restored_total_ + received_overflows;
  if (total != this->saved_total_) {
    if (this->preference_.save(&total)) {
      this->saved_total_ = total;
    } else {
      ESP_LOGW(TAG, "Could not queue overflow counter for saving");
    }
  }
  if (!this->has_state() || total != this->published_total_) {
    this->publish_state(total);
    this->published_total_ = total;
  }
}

void UARTOverflowSensor::on_shutdown() {
  this->update();
  global_preferences->sync();
}

void UARTOverflowSensor::dump_config() {
  LOG_SENSOR("", "UART RX Overflows", this);
  ESP_LOGCONFIG(TAG, "  UART%d, actual RX buffer: %u bytes", this->port_ + 1, LT_SERIAL_BUFFER_SIZE);
  LOG_UPDATE_INTERVAL(this);
}

}  // namespace esphome::bk72xx_uart_guard

extern "C" int __real_uart_read_byte(int port);
extern "C" int __wrap_uart_read_byte(int port) {
  const int value = __real_uart_read_byte(port);
  if (value < 0)
    return value;
  SerialClass *serial = nullptr;
#if LT_HW_UART1
  if (port == 0)
    serial = &Serial1;
#endif
#if LT_HW_UART2
  if (port == 1)
    serial = &Serial2;
#endif
  // LibreTiny's RX callback calls store_char() immediately after this byte read.
  // A full software ring discards that incoming byte without advancing its head.
  if (serial != nullptr && serial->available() == LT_SERIAL_BUFFER_SIZE)
    ++esphome::bk72xx_uart_guard::overflow_count[port];
  return value;
}
#endif
