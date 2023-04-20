/*===- StandaloneFuzzTargetMain.c - standalone main() for fuzz targets. ---===//
//
// Part of the LLVM Project, under the Apache License v2.0 with LLVM Exceptions.
// See https://llvm.org/LICENSE.txt for license information.
// SPDX-License-Identifier: Apache-2.0 WITH LLVM-exception
//
//===----------------------------------------------------------------------===//
// This main() function can be linked to a fuzz target (i.e. a library
// that exports LLVMFuzzerTestOneInput() and possibly LLVMFuzzerInitialize())
// instead of libFuzzer. This main() function will not perform any fuzzing
// but will simply feed all input files one by one to the fuzz target.
//
// Use this file to provide reproducers for bugs when linking against libFuzzer
// or other fuzzing engine is undesirable.
//===----------------------------------------------------------------------===*/
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <unistd.h>

// Input buffer.
static const size_t kMaxAflInputSize = 1 << 20;
static uint8_t AflInputBuf[kMaxAflInputSize];

extern "C" {

__attribute__((weak))
extern int LLVMFuzzerTestOneInput(const unsigned char *data, size_t size);
__attribute__((weak))
extern int LLVMFuzzerInitialize(int *argc, char ***argv);
__attribute__((weak))
int main(int argc, char **argv) {
  if (LLVMFuzzerInitialize)
    LLVMFuzzerInitialize(&argc, &argv);
  if (argc > 1) {
    for (int i = 1; i < argc; i++) {
      FILE *f = fopen(argv[i], "r");
      assert(f);
      fseek(f, 0, SEEK_END);
      size_t len = ftell(f);
      fseek(f, 0, SEEK_SET);
      unsigned char *buf = (unsigned char*)malloc(len);
      size_t n_read = fread(buf, 1, len, f);
      fclose(f);
      assert(n_read == len);
      LLVMFuzzerTestOneInput(buf, len);
      free(buf);
    }
  } else {
    ssize_t n_read = read(0, AflInputBuf, kMaxAflInputSize);
    if (n_read > 0) {
      // Copy AflInputBuf into a separate buffer to let asan find buffer
      // overflows. Don't use unique_ptr/etc to avoid extra dependencies.
      uint8_t *copy = new uint8_t[n_read];
      memcpy(copy, AflInputBuf, n_read);
      LLVMFuzzerTestOneInput(copy, n_read);
      delete[] copy;
    }
  }
  return 0;
}

}