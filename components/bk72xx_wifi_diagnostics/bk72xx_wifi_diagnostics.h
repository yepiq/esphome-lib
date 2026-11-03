#pragma once

#include <atomic>
#include "diagnostic_state.h"
#include "esphome/core/component.h"
#include "esphome/core/preferences.h"
#include "esphome/components/sensor/sensor.h"
#include "esphome/components/text_sensor/text_sensor.h"
#include <FreeRTOS.h>
#include <queue.h>

struct pbuf;

namespace esphome::bk72xx_wifi_diagnostics {

class WiFiDiagnostics : public PollingComponent {
 public:
  void setup() override;
  void loop() override;
  void update() override;
  void dump_config() override;
  void on_shutdown() override;
  float get_setup_priority() const override { return setup_priority::WIFI + 1; }
  void set_counter(size_t index, sensor::Sensor *value) { this->counters_[index] = value; }
  void set_event_history(text_sensor::TextSensor *value) { this->event_history_ = value; }
  void set_rx_snapshot(text_sensor::TextSensor *value) { this->rx_snapshot_ = value; }
  void observe_rx(int iface, struct pbuf *packet);
  void restart_wifi();
  void snapshot();

 protected:
  struct PendingEvent { uint32_t at_ms; Event event; uint8_t reason; };
  void enqueue_(Event event, uint8_t reason);
  void drain_events_();
  void collect_();
  void persist_();
  void record_(Event event, uint8_t reason = 0);
  void publish_();
  DiagnosticState state_{};
  ESPPreferenceObject preference_;
  sensor::Sensor *counters_[COUNTER_COUNT]{};
  text_sensor::TextSensor *event_history_{};
  text_sensor::TextSensor *rx_snapshot_{};
  QueueHandle_t events_{};
  // ethernetif_input has one producer: Beken's RX task. Avoid atomic RMW on ARMv5.
  std::atomic<uint32_t> received_[COUNTER_COUNT]{};
  uint32_t collected_[COUNTER_COUNT]{};
  std::atomic<uint32_t> dropped_events_{0};
  uint32_t dropped_collected_{0};
  uint32_t saved_at_{0};
  bool restarting_{false};
};

}  // namespace esphome::bk72xx_wifi_diagnostics
