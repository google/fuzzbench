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

#include <stdlib.h>
#include <stdint.h>

// these are defined in the LLVM passes, 
// but need to be mocked for persistent mode.
void __afl_manual_init(void) { printf("manual_init\n"); }
int __afl_persistent_loop(unsigned int max_cnt) { printf("peristent loop\n"); return 0; }
uint32_t __afl_get_area_size(void) { printf("get area size\n"); return 0; }
uint32_t __afl_get_bbarea_size(void) { printf("bb area size\n"); return 0; }