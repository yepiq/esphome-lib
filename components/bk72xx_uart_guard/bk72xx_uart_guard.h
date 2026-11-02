#pragma once

#include <cstdint>

namespace esphome::bk72xx_uart_guard {

uint32_t save_and_mask_irq_fiq();
void restore_irq_fiq(uint32_t saved);

}  // namespace esphome::bk72xx_uart_guard
