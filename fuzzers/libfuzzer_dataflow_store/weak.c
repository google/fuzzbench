#include <stdint.h>

__attribute__((weak)) void __sanitizer_cov_load1(uint8_t *addr) {}
__attribute__((weak)) void __sanitizer_cov_load2(uint16_t *addr) {}
__attribute__((weak)) void __sanitizer_cov_load4(uint32_t *addr) {}
__attribute__((weak)) void __sanitizer_cov_load8(uint64_t *addr) {}
__attribute__((weak)) void __sanitizer_cov_load16(__uint128_t *addr) {}

__attribute__((weak)) void __sanitizer_cov_store1(uint8_t *addr) {}
__attribute__((weak)) void __sanitizer_cov_store2(uint16_t *addr) {}
__attribute__((weak)) void __sanitizer_cov_store4(uint32_t *addr) {}
__attribute__((weak)) void __sanitizer_cov_store8(uint64_t *addr) {}
__attribute__((weak)) void __sanitizer_cov_store16(__uint128_t *addr) {}

