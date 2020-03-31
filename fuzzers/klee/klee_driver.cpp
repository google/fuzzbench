#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

//TODO: include klee/klee.h when KLEE is installed
extern "C" {
  // Functon defined by benchmarks as entry point
  int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);
  // KLEE's internal functions
  void klee_make_symbolic(void *addr, size_t nbytes, const char *name);
}

// Input buffer.
const size_t kKleeInputSize = 4096;
uint8_t KleeInputBuf[kKleeInputSize];


int main(int argc, char **argv) {
  klee_make_symbolic(KleeInputBuf, kKleeInputSize, "KleeInputBuf");
  return LLVMFuzzerTestOneInput(KleeInputBuf, kKleeInputSize);
}
