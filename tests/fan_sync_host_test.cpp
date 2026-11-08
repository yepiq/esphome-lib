#include <cassert>
#include <cmath>
#include <cstdint>
#include <functional>
#include <iostream>
#include <optional>
#include <string>
#include <vector>

#define id(value) value
#define ESP_LOGD(...) ((void) 0)

std::vector<std::string> writes;

struct Switch {
  std::string label;
  bool state{false};
  void turn_on() { writes.push_back(label + ":on"); state = true; }
  void turn_off() { writes.push_back(label + ":off"); state = false; }
} pb_power_dp{"pb-power"}, pb_swing_dp{"pb-swing"}, jummico_power_dp{"j-power"};

struct Number {
  float state{0};
  struct Call {
    Number *parent;
    float value{0};
    void set_value(float value) { this->value = value; }
    void perform() { writes.push_back("pb-speed:" + std::to_string(int(value))); parent->state = value; }
  };
  Call make_call() { return {this}; }
  void publish_state(float value) { state = value; }
} pb_fan_speed_dp;

struct Tuya {
  void set_enum_datapoint_value(uint8_t dp, uint8_t value) {
    assert(dp == 4);
    writes.push_back("j-speed:" + std::to_string(value));
  }
  void force_set_enum_datapoint_value(uint8_t dp, uint8_t value) {
    assert(dp == 6);
    writes.push_back("pb-speed:" + std::to_string(value));
  }
} jummico_tuya, pb_tuya;
int jummico_fan_speed_dp{-1};
bool jummico_syncing_fan{false};
bool pb_syncing_fan{false};
int pb_mcu_power_state{-1};
int pb_startup_speed{0};

struct Fan {
  bool state{false};
  int speed{0};
  bool oscillating{false};
  struct Call;
  std::function<void(const Call &)> control_callback;
  std::function<void(Fan *)> callback;
  struct Call {
    Fan *parent;
    std::optional<bool> state, oscillating;
    std::optional<int> speed;
    void set_state(bool value) { state = value; }
    void set_speed(int value) { speed = value; }
    void set_oscillating(bool value) { oscillating = value; }
    std::optional<bool> get_state() const { return state; }
    std::optional<int> get_speed() const { return speed; }
    void perform() {
      if (parent->control_callback) parent->control_callback(*this);
      if (state) parent->state = *state;
      if (speed) parent->speed = *speed;
      if (oscillating) parent->oscillating = *oscillating;
      parent->callback(parent);
    }
  };
  Call make_call() { return {this}; }
} pb_fan, jummico_fan;

void pb_control(const Fan::Call &x) { PB_CONTROL_BODY }
void pb_command(Fan *x) { PB_COMMAND_BODY }
void jummico_command(Fan *x) { JUMMICO_COMMAND_BODY }
void pb_power_update(bool x) { PB_DP1_BODY }
void pb_speed_update(uint8_t x) { PB_DP6_BODY }
void pb_swing_update(bool x) { PB_DP8_BODY }
void jummico_power_update(bool x) { JUMMICO_DP1_BODY }
void jummico_speed_update(uint8_t x) { JUMMICO_DP4_BODY }

int main() {
  pb_fan.control_callback = pb_control;
  pb_fan.callback = pb_command;
  jummico_fan.callback = jummico_command;
  int cases = 0;
  for (bool power : {false, true}) for (bool on : {false, true})
  for (bool swing : {false, true}) for (bool oscillating : {false, true})
  for (int known : {0, 1}) for (int speed : {0, 1, 2, 3}) {
    pb_mcu_power_state = 1;
    pb_power_dp.state = power;
    pb_swing_dp.state = swing;
    pb_fan_speed_dp.state = known;
    pb_fan.state = on;
    pb_fan.oscillating = oscillating;
    pb_fan.speed = speed;
    writes.clear();
    std::vector<std::string> expected;
    if (power != on) expected.push_back(on ? "pb-power:on" : "pb-power:off");
    if (on && swing != oscillating) expected.push_back(oscillating ? "pb-swing:on" : "pb-swing:off");
    if (on && (speed == 1 || speed == 2) && known != (speed == 1 ? 1 : 0))
      expected.push_back("pb-speed:" + std::to_string(speed == 1 ? 1 : 0));
    pb_command(&pb_fan);
    assert(writes == expected);
    ++cases;
  }
  for (bool guarded : {false, true}) for (bool power : {false, true})
  for (bool on : {false, true}) for (int known : {-1, 0, 1}) for (int speed : {0, 1, 2, 3}) {
    jummico_syncing_fan = guarded;
    jummico_power_dp.state = power;
    jummico_fan_speed_dp = known;
    jummico_fan.state = on;
    jummico_fan.speed = speed;
    writes.clear();
    std::vector<std::string> expected;
    if (!guarded) {
      if (power != on) expected.push_back(on ? "j-power:on" : "j-power:off");
      if (on && (speed == 1 || speed == 2) && known != speed - 1)
        expected.push_back("j-speed:" + std::to_string(speed - 1));
    }
    jummico_command(&jummico_fan);
    assert(writes == expected);
    ++cases;
  }

  // MCU readback uses the real device callbacks, including reentrant fan commands.
  for (int known : {-1, 0, 1}) for (bool power : {false, true}) {
    jummico_syncing_fan = false;
    jummico_power_dp.state = power;
    jummico_fan_speed_dp = known;
    jummico_fan.speed = 2;
    writes.clear();
    jummico_power_update(power);
    assert(jummico_fan.state == power && !jummico_syncing_fan && writes.empty());
    assert(jummico_fan.speed == (power && known >= 0 ? known + 1 : 2));
  }
  for (uint8_t value : {0, 1, 2, 255}) {
    jummico_fan_speed_dp = -1;
    jummico_fan.speed = 2;
    writes.clear();
    jummico_speed_update(value);
    assert(!jummico_syncing_fan && writes.empty());
    assert(jummico_fan_speed_dp == (value <= 1 ? value : -1));
    assert(jummico_fan.speed == (value <= 1 ? value + 1 : 2));
  }
  // Repeated power feedback preserves speed and never commands the MCU, even
  // when the backing switch/number listeners have not received this report yet.
  for (bool cached_power : {false, true}) for (bool power : {false, true})
  for (int speed : {1, 2}) {
    pb_syncing_fan = false;
    pb_mcu_power_state = power ? 1 : 0;
    pb_power_dp.state = cached_power;
    pb_fan.speed = speed;
    writes.clear();
    pb_power_update(power);
    pb_power_update(power);
    assert(pb_fan.state == power && pb_fan.speed == speed);
    assert(!pb_syncing_fan && writes.empty());
  }
  // First report after an ESP reboot must preserve an already-running High.
  pb_mcu_power_state = -1;
  pb_fan.speed = 2;
  writes.clear();
  pb_power_update(true);
  assert(pb_fan.speed == 2 && writes.empty());

  // An appliance power cycle silently resets speed, even with stale DP6=High.
  pb_power_update(false);
  pb_fan_speed_dp.state = 0;
  pb_power_update(true);
  assert(pb_fan.state && pb_fan.speed == 1 && pb_fan_speed_dp.state == 1);
  assert(!pb_syncing_fan && writes.empty());
  pb_power_update(true);
  assert(pb_fan.speed == 1 && writes.empty());

  // A subsequent HA High command must be sent despite Tuya's stale High cache.
  pb_power_dp.state = true;
  pb_swing_dp.state = pb_fan.oscillating;
  pb_fan.speed = 2;
  pb_command(&pb_fan);
  assert(writes == std::vector<std::string>{"pb-speed:0"});
  pb_speed_update(0);
  writes.clear();
  pb_power_update(true);
  assert(pb_fan.speed == 2 && writes.empty());

  for (bool power : {false, true}) for (uint8_t value : {0, 1}) {
    pb_fan.state = power;
    pb_power_dp.state = !power;
    pb_fan_speed_dp.state = 1 - value;
    writes.clear();
    pb_speed_update(value);
    assert(pb_fan.state == power && pb_fan.speed == (value == 1 ? 1 : 2));
    assert(!pb_syncing_fan && writes.empty());
  }
  for (bool swing : {false, true}) {
    pb_fan.state = true;
    pb_power_dp.state = false;
    pb_swing_dp.state = !swing;
    writes.clear();
    pb_swing_update(swing);
    assert(pb_fan.oscillating == swing && !pb_syncing_fan && writes.empty());
  }
  // Startup intent must survive MCU Low defaults, even when previous speed was High.
  for (int requested_speed : {0, 1, 2}) {
    pb_mcu_power_state = 0;
    pb_startup_speed = 0;
    pb_fan.state = false;
    pb_fan.speed = 2;
    pb_power_dp.state = false;
    pb_fan_speed_dp.state = 0;
    pb_swing_dp.state = pb_fan.oscillating;
    writes.clear();
    auto on = pb_fan.make_call();
    on.set_state(true);
    if (requested_speed) on.set_speed(requested_speed);
    on.perform();
    assert(pb_startup_speed == requested_speed);
    assert(writes == std::vector<std::string>{"pb-power:on"});
    // A Low report may arrive before the power acknowledgment.
    pb_speed_update(1);
    pb_fan_speed_dp.state = 1;
    pb_power_update(true);
    assert(pb_fan.state && pb_fan.speed == (requested_speed ? requested_speed : 1));
    assert(pb_startup_speed == 0 && !pb_syncing_fan);
    if (requested_speed == 2) {
      assert(writes == (std::vector<std::string>{"pb-power:on", "pb-speed:0"}));
      pb_speed_update(0);
    } else {
      assert(writes == std::vector<std::string>{"pb-power:on"});
    }
    writes.clear();
    pb_power_update(true);
    assert(pb_fan.speed == (requested_speed ? requested_speed : 1) && writes.empty());
  }
  // Off cancels a startup request before the MCU acknowledges power.
  pb_mcu_power_state = 0;
  pb_startup_speed = 2;
  auto off = pb_fan.make_call();
  off.set_state(false);
  off.perform();
  assert(pb_startup_speed == 0);
  std::cout << "PASS " << cases << " fan command combinations and MCU feedback checks\n";
}
