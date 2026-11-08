#pragma once

#include "esphome/core/automation.h"
#include "esphome/core/component.h"
#include "esphome/components/fan/fan.h"

namespace esphome::command_fan {

// A template-style fan with the original command fields available before state changes.
class CommandFan : public Component, public fan::Fan {
 public:
  void set_speed_count(int count) { speed_count_ = count; this->speed = 1; }
  void set_has_oscillating(bool value) { has_oscillating_ = value; }
  fan::FanTraits get_traits() override { return {has_oscillating_, true, false, speed_count_}; }
  void setup() override {
    auto restored = this->restore_state_();
    if (restored.has_value()) restored->apply(*this);
  }
  void add_on_control_callback(std::function<void(const fan::FanCall &)> callback) {
    control_callback_.add(std::move(callback));
  }

 protected:
  void control(const fan::FanCall &call) override {
    control_callback_.call(call);
    if (call.get_state().has_value()) this->state = *call.get_state();
    if (call.get_speed().has_value()) this->speed = *call.get_speed();
    if (call.get_oscillating().has_value()) this->oscillating = *call.get_oscillating();
    this->publish_state();
  }
  int speed_count_{1};
  bool has_oscillating_{false};
  CallbackManager<void(const fan::FanCall &)> control_callback_;
};

class CommandTrigger : public Trigger<const fan::FanCall &> {
 public:
  explicit CommandTrigger(CommandFan *parent) {
    parent->add_on_control_callback([this](const fan::FanCall &call) { this->trigger(call); });
  }
};

}  // namespace esphome::command_fan
