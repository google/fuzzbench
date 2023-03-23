#!/bin/bash
FUZZERS=(symcts symcts_afl symcts_symqemu symcts_symqemu_afl honggfuzz libfuzzer symcc_aflplusplus)
TARGETS=(libxml2-v2.9.2 libpng-1.6.38 freetype2-2017)

MAKEFILETARGETS=()

for fuzzer in ${FUZZERS[@]}
do
    for target in ${TARGETS[@]}
    do
        MAKEFILETARGETS+=(build-$fuzzer-$target)
    done
done

echo ${MAKEFILETARGETS[@]}
make ${MAKEFILETARGETS[@]} -j 4