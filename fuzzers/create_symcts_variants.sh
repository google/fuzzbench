#!/bin/bash

set -e
# set -x

# VARIANTS=(afl_companion symcc_afl symqemu_afl)
VARIANTS=()
VARIANTS+=(symcts symcts_afl symcts_weak symcts_afl_weak)
VARIANTS+=(symcts_symqemu symcts_symqemu_afl symcts_symqemu_weak symcts_symqemu_afl_weak )
VARIANTS+=(afl_companion)
#VARIANTS+=(symcts_context_sensitive symcts_decision_coverage)

FILES=(builder.Dockerfile build_zlib.sh fuzzer.py runner.Dockerfile src/afl_driver.cpp)
for VARIANT in "${VARIANTS[@]}"; do
    echo "Creating variant $VARIANT"
    rm -rf "$VARIANT"
    mkdir -p "$VARIANT/src/"
    for f in "${FILES[@]}"; do
        cp "BASE_symcts/$f" "$VARIANT/$f"
    done
done
