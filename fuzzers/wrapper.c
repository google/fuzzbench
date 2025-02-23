#include <stdlib.h>
#include <stdio.h>
#include <stdint.h>

int __real_LLVMFuzzerTestOneInput(uint8_t* data, size_t size);

int __wrap_LLVMFuzzerTestOneInput(uint8_t* data, size_t size) {
  printf("__wrap_LLVMFuzzerTestOneInput\n");
  return __real_LLVMFuzzerTestOneInput(data, size);
}
