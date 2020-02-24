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
// clang -fsanitize-coverage=trace-pc-guard -O1 \
//     third_party/StandaloneFuzzTargetMain.c fuzz_target.cc -o fuzz-target

#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t* data, size_t size) {
  if (size < 0)
    return 0;

  if (data[0] == 'a')
    abort();
  if (size < 4)
    return 0;
  if (data[0] == 't' && data[1] == 'i' && data[2] == 'm' && data[3] == 'e')
    while (true) ;

  return 0;
}
