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

// Compile using:
// clang -fsanitize=fuzzer -fsanitize=address,undefined -O1 -gline-tables-only \
//     fuzz_target.c -o fuzz-target

#include <stdint.h>
#include <stdlib.h>

int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  if (size < 0)
    return 0;

  if (data[0] == 'a')
    abort();
  if (size < 4)
    return 0;
  if (data[0] == 't' && data[1] == 'i' && data[2] == 'm' && data[3] == 'e')
    while (1) ;

  return 0;
}
