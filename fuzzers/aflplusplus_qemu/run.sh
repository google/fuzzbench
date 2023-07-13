#!/bin/bash
# Copyright 2020 AFLplusplus
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
test -x "$1" || { echo Error: $1 is not an executable; exit 1; }
ADDR=`qemu_get_symbol_addr.sh $1 LLVMFuzzerTestOneInput`
test -n "$ADDR" || { echo Error: $1 does not contain LLVMFuzzerTestOneInput; exit 1; }
export AFL_ENTRYPOINT=$ADDR
export AFL_QEMU_PERSISTENT_ADDR=$ADDR
export AFL_QEMU_PERSISTENT_CNT=1000000
export AFL_QEMU_PERSISTENT_HOOK=/out/aflpp_qemu_driver_hook.so
export AFL_PATH=/out
export AFL_CMPLOG_ONLY_NEW=1
export AFL_DISABLE_TRIM=1
export AFL_NO_WARN_INSTABILITY=1
export AFL_FAST_CAL=1
export AFL_IGNORE_UNKNOWN_ENVS=1
export AFL_MAP_SIZE=2621440
cd seeds && { 
  for i in ../*.zip; do unzip -n $i; done
  echo > empty_testcase.txt
  cd ..
}
./afl-fuzz -Q -i seeds -o corpus -c 0 -l 2 -- $1
