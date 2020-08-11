// Copyright 2020 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//      http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#include <assert.h>
#include <errno.h>
#include <stdarg.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

//TODO: include klee/klee.h when KLEE is installed
extern "C"
{
  // Functon defined by benchmarks as entry point
  int LLVMFuzzerTestOneInput(const uint8_t *Data, size_t Size);
  // KLEE's internal functions
  void klee_make_symbolic(void *addr, size_t nbytes, const char *name);
}

// Input buffer.
size_t kleeInputSize = 4096;

int main(int argc, char **argv)
{
  kleeInputSize = atoi(argv[1]);
  uint8_t *kleeInputBuf = (uint8_t *)malloc(kleeInputSize * sizeof(uint8_t));
  printf("kleeInputSize: %zu\n", kleeInputSize);

  klee_make_symbolic(kleeInputBuf, kleeInputSize, "kleeInputBuf");
  int result = LLVMFuzzerTestOneInput(kleeInputBuf, kleeInputSize);

  free(kleeInputBuf);
  return result;
}
