#include "bk72xx_wifi_diagnostics.h"
#include "esphome/core/log.h"
#include "esphome/components/wifi/wifi_component.h"
#include <WiFi.h>
#include <algorithm>
#include <cinttypes>
#include <cstdio>
#include <lwip/pbuf.h>

extern "C" {
struct netif *rwm_mgmt_get_vif2netif(uint8_t vif_idx);
void *net_get_sta_handle(void);
void __real_ethernetif_input(int iface, struct pbuf *packet);
}

namespace esphome::bk72xx_wifi_diagnostics {

static const char *const TAG = "wifi_diag";
static WiFiDiagnostics *instance;
// Fixed key/schema: firmware rebuilds and OTA must not reset the investigation.
static constexpr uint32_t PREFERENCE_KEY = 0xB723D101;
static constexpr uint32_t SAVE_INTERVAL_MS = 300000;

static const char *event_name(Event event) {
  switch (event) {
    case Event::BOOT: return "boot";
    case Event::START: return "start";
    case Event::STOP: return "stop";
    case Event::CONNECTED: return "up";
    case Event::DISCONNECTED: return "down";
    case Event::GOT_IP: return "ip";
    case Event::RESTART: return "restart";
    case Event::SHUTDOWN: return "shutdown";
    case Event::QUEUE_OVERFLOW: return "lost";
    default: return "unknown";
  }
}

void WiFiDiagnostics::setup() {
  this->preference_ = global_preferences->make_preference<DiagnosticState>(PREFERENCE_KEY);
  if (!this->preference_.load(&this->state_) || !this->state_.valid())
    this->state_ = DiagnosticState{};
  this->state_.boots++;
  this->events_ = xQueueCreate(16, sizeof(PendingEvent));
  if (this->events_ == nullptr) {
    this->mark_failed();
    return;
  }
  instance = this;
  WiFi.onEvent([this](WiFiEvent_t event, WiFiEventInfo_t info) {
    switch (event) {
      case ARDUINO_EVENT_WIFI_STA_START: this->enqueue_(Event::START, 0); break;
      case ARDUINO_EVENT_WIFI_STA_STOP: this->enqueue_(Event::STOP, 0); break;
      case ARDUINO_EVENT_WIFI_STA_CONNECTED: this->enqueue_(Event::CONNECTED, 0); break;
      case ARDUINO_EVENT_WIFI_STA_DISCONNECTED:
        this->enqueue_(Event::DISCONNECTED, info.wifi_sta_disconnected.reason);
        break;
      case ARDUINO_EVENT_WIFI_STA_GOT_IP: this->enqueue_(Event::GOT_IP, 0); break;
      default: break;
    }
  });
  this->record_(Event::BOOT);
  this->persist_();
}

void WiFiDiagnostics::observe_rx(int iface, struct pbuf *packet) {
  if (packet == nullptr || rwm_mgmt_get_vif2netif(static_cast<uint8_t>(iface)) != net_get_sta_handle())
    return;
  uint8_t header[14];
  const auto length = pbuf_copy_partial(packet, header, sizeof(header), 0);
  const int index = classify_frame(header, length);
  if (index >= 0) {
    auto &counter = this->received_[index];
    counter.store(counter.load(std::memory_order_relaxed) + 1, std::memory_order_relaxed);
  }
}

void WiFiDiagnostics::enqueue_(Event event, uint8_t reason) {
  PendingEvent pending{millis(), event, reason};
  if (xQueueSend(this->events_, &pending, 0) != pdTRUE)
    this->dropped_events_.store(this->dropped_events_.load(std::memory_order_relaxed) + 1,
                                std::memory_order_relaxed);
}

void WiFiDiagnostics::collect_() {
  for (size_t i = 0; i < COUNTER_COUNT; i++) {
    const uint32_t now = this->received_[i].load(std::memory_order_relaxed);
    this->state_.packets[i] += counter_delta(now, this->collected_[i]);
    this->collected_[i] = now;
  }
}

void WiFiDiagnostics::record_(Event event, uint8_t reason) {
  this->state_.record(event, millis(), reason, WiFi.getSleep());
}

void WiFiDiagnostics::drain_events_() {
  PendingEvent event;
  bool changed = false;
  while (xQueueReceive(this->events_, &event, 0) == pdTRUE) {
    this->state_.record(event.event, event.at_ms, event.reason, WiFi.getSleep());
    changed = true;
  }
  const uint32_t dropped = this->dropped_events_.load(std::memory_order_relaxed);
  if (dropped != this->dropped_collected_) {
    this->record_(Event::QUEUE_OVERFLOW, static_cast<uint8_t>(std::min<uint32_t>(255, dropped - this->dropped_collected_)));
    this->dropped_collected_ = dropped;
    changed = true;
  }
  if (changed) {
    this->collect_();
    this->persist_();
    this->publish_();
  }
}

void WiFiDiagnostics::persist_() {
  if (!this->preference_.save(&this->state_) || !global_preferences->sync()) {
    ESP_LOGW(TAG, "Could not persist diagnostic state");
    return;
  }
  this->saved_at_ = millis();
}

void WiFiDiagnostics::loop() { this->drain_events_(); }

void WiFiDiagnostics::update() {
  this->collect_();
  this->publish_();
  if (millis() - this->saved_at_ >= SAVE_INTERVAL_MS)
    this->persist_();
}

void WiFiDiagnostics::publish_() {
  for (size_t i = 0; i < COUNTER_COUNT; i++)
    this->counters_[i]->publish_state(this->state_.packets[i]);
  // Exact uint64 counts remain available when HA's float sensor rounds large totals.
  char buffer[240];
  snprintf(buffer, sizeof(buffer), "boot=%" PRIu32 " sleep=%u ipv4=%" PRIu64 "/%" PRIu64
           " arp=%" PRIu64 "/%" PRIu64 " eapol=%" PRIu64 "/%" PRIu64,
           this->state_.boots, unsigned(WiFi.getSleep()), this->state_.packets[0], this->state_.packets[1],
           this->state_.packets[2], this->state_.packets[3], this->state_.packets[4], this->state_.packets[5]);
  this->rx_snapshot_->publish_state(buffer);
  std::string history;
  const auto count = std::min<uint32_t>(6, this->state_.history_count);
  for (uint32_t i = count; i > 0; i--) {
    const auto &event = this->state_.history[(this->state_.history_next + HISTORY_SIZE - i) % HISTORY_SIZE];
    snprintf(buffer, sizeof(buffer), "%sb%" PRIu32 "+%" PRIu32 "s %s:%u",
             history.empty() ? "" : ";", event.boot, event.at_ms / 1000, event_name(event.event), unsigned(event.reason));
    history += buffer;
  }
  this->event_history_->publish_state(history);
}

void WiFiDiagnostics::snapshot() {
  this->drain_events_();
  this->collect_();
  this->persist_();
  this->publish_();
  ESP_LOGI(TAG, "%s", this->rx_snapshot_->state.c_str());
  for (uint32_t i = this->state_.history_count; i > 0; i--) {
    const auto &event = this->state_.history[(this->state_.history_next + HISTORY_SIZE - i) % HISTORY_SIZE];
    ESP_LOGI(TAG, "boot=%" PRIu32 " ms=%" PRIu32 " %s reason=%u sleep=%u", event.boot, event.at_ms,
             event_name(event.event), unsigned(event.reason), unsigned(event.sleep));
  }
}

void WiFiDiagnostics::restart_wifi() {
  if (this->restarting_ || wifi::global_wifi_component->is_disabled())
    return;
  this->restarting_ = true;
  this->record_(Event::RESTART);
  this->snapshot();
  // Arm re-enable before tearing down the API transport. No relay/MCU restart.
  this->set_timeout("wifi_reenable", 5000, [this]() {
    wifi::global_wifi_component->enable();
    this->restarting_ = false;
  });
  wifi::global_wifi_component->disable();
}

void WiFiDiagnostics::on_shutdown() {
  if (this->is_failed())
    return;
  this->drain_events_();
  this->collect_();
  this->record_(Event::SHUTDOWN);
  this->persist_();
}

void WiFiDiagnostics::dump_config() {
  ESP_LOGCONFIG(TAG, "BK7231N WiFi diagnostics: persistent counters/events, 5min checkpoints");
}

}  // namespace esphome::bk72xx_wifi_diagnostics

extern "C" void __wrap_ethernetif_input(int iface, struct pbuf *packet) {
  if (esphome::bk72xx_wifi_diagnostics::instance != nullptr)
    esphome::bk72xx_wifi_diagnostics::instance->observe_rx(iface, packet);
  __real_ethernetif_input(iface, packet);
}
