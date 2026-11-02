#include "bk72xx_uart_guard.h"
#include "esphome/core/defines.h"
#include <Arduino.h>

#if LT_ARD_HAS_SERIAL
#include <Serial.h>

namespace esphome::bk72xx_uart_guard {

#ifndef USE_HOST
#if !defined(__arm__) || __ARM_ARCH != 5
#error "bk72xx_uart_guard requires Beken's ARMv5 core"
#endif

// Preserve both masks together, including callers that already disabled interrupts.
__attribute__((target("arm"), noinline)) uint32_t save_and_mask_irq_fiq() {
  uint32_t saved, masked;
  asm volatile("mrs %0, cpsr\n\torr %1, %0, #0xc0\n\tmsr cpsr_c, %1"
               : "=&r"(saved), "=&r"(masked) : : "memory", "cc");
  return saved;
}

__attribute__((target("arm"), noinline)) void restore_irq_fiq(uint32_t saved) {
  uint32_t current;
  asm volatile("mrs %0, cpsr\n\tbic %0, %0, #0xc0\n\tand %1, %1, #0xc0\n\torr %0, %0, %1\n\tmsr cpsr_c, %0"
               : "=&r"(current), "+r"(saved) : : "memory", "cc");
}
#endif

}  // namespace esphome::bk72xx_uart_guard

extern "C" int __real__ZN11SerialClass4readEv(SerialClass *self);
extern "C" int __wrap__ZN11SerialClass4readEv(SerialClass *self) {
  const uint32_t saved = esphome::bk72xx_uart_guard::save_and_mask_irq_fiq();
  const int value = __real__ZN11SerialClass4readEv(self);
  esphome::bk72xx_uart_guard::restore_irq_fiq(saved);
  return value;
}
#endif
