#pragma once

#include <cstddef>
#include <cstdint>

namespace esphome::bk72xx_wifi_diagnostics {

static constexpr size_t COUNTER_COUNT = 6;
static constexpr size_t HISTORY_SIZE = 12;
static constexpr uint32_t STATE_VERSION = 1;

enum class Event : uint8_t { BOOT, START, STOP, CONNECTED, DISCONNECTED, GOT_IP, RESTART, SHUTDOWN, QUEUE_OVERFLOW };

struct EventRecord {
  uint32_t boot;
  uint32_t at_ms;
  Event event;
  uint8_t reason;
  uint8_t sleep;
  uint8_t reserved;
};

struct DiagnosticState {
  uint32_t version{STATE_VERSION};
  uint32_t boots{0};
  uint64_t packets[COUNTER_COUNT]{};
  EventRecord history[HISTORY_SIZE]{};
  uint32_t history_next{0};
  uint32_t history_count{0};

  bool valid() const {
    if (this->version != STATE_VERSION || this->history_next >= HISTORY_SIZE || this->history_count > HISTORY_SIZE)
      return false;
    for (size_t i = 0; i < this->history_count; i++)
      if (this->history[i].event > Event::QUEUE_OVERFLOW)
        return false;
    return true;
  }

  void record(Event event, uint32_t at_ms, uint8_t reason = 0, bool sleep = false) {
    this->history[this->history_next] = {this->boots, at_ms, event, reason, uint8_t(sleep), 0};
    this->history_next = (this->history_next + 1) % HISTORY_SIZE;
    if (this->history_count < HISTORY_SIZE)
      this->history_count++;
  }
};

// A bounded Ethernet header copied with pbuf_copy_partial(), including split pbufs.
// Group includes both broadcast and multicast; other EtherTypes are deliberately ignored.
inline int classify_frame(const uint8_t *header, size_t length) {
  if (length < 14)
    return -1;
  const uint16_t type = (uint16_t(header[12]) << 8) | header[13];
  const int group = header[0] & 1;
  switch (type) {
    case 0x0800: return group;
    case 0x0806: return 2 + group;
    case 0x888E: return 4 + group;
    default: return -1;
  }
}

inline uint32_t counter_delta(uint32_t current, uint32_t previous) { return current - previous; }

}  // namespace esphome::bk72xx_wifi_diagnostics
