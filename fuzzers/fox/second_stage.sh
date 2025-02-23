#!/bin/bash

set -e

# based on targets/mbedtls/build_aflpp.sh from adamstorek/fox: https://github.com/FOX-Fuzz/FOX/blob/main/README_StandAlone.md

get-bc $FUZZ_TARGET
llvm-dis $FUZZ_TARGET.bc
python /afl/fix_long_fun_name.py $FUZZ_TARGET.ll
mkdir -p cfg_out_$FUZZ_TARGET
cd cfg_out_$FUZZ_TARGET
opt -dot-cfg ../$FUZZ_TARGET\_fix.ll
for f in $(ls -a | grep '^\.*'|grep dot);do mv $f ${f:1};done
cd ..

python /afl/gen_graph_dev_refactor.py $FUZZ_TARGET\_fix.ll cfg_out_$FUZZ_TARGET $PWD/$FUZZ_TARGET instrument_meta_data
