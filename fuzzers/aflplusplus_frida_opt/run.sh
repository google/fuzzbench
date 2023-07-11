#!/bin/sh
test -x "$1" || { echo Error: $1 is not an executable; exit 1; }
ADDR=0x`nm "$1"|grep -i 'T LLVMFuzzerTestOneInput'|awk '{print$1}'`
test -n "$ADDR" || { echo Error: $1 does not contain LLVMFuzzerTestOneInput; exit 1; }
export AFL_FRIDA_PERSISTENT_ADDR=$ADDR
export AFL_ENTRYPOINT=$ADDR
export AFL_FRIDA_PERSISTENT_HOOK=/out/frida_hook.so
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
./afl-fuzz -O -i seeds -o corpus -c 0 -l 2 -- $1
