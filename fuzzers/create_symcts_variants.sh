#!/bin/bash

# Copyright 2020 Google LLC
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


set -e
# set -x

# VARIANTS=(afl_companion symcc_afl symqemu_afl)
VARIANTS=()
VARIANTS+=(symcts symcts_afl)
#VARIANTS+=(symcts_sampling symcts_afl_sampling)
VARIANTS+=(symcts_symqemu symcts_symqemu_afl)
#VARIANTS+=(symcts_symqemu_sampling symcts_symqemu_afl_sampling)
VARIANTS+=(afl_companion)
#VARIANTS+=(symcts_context_sensitive symcts_decision_coverage)

FILES=(builder.Dockerfile build_zlib.sh fuzzer.py runner.Dockerfile run_with_multilog.sh src/afl_driver.cpp)
for VARIANT in "${VARIANTS[@]}"; do
    echo "Creating variant $VARIANT"
    rm -rf "$VARIANT"
    mkdir -p "$VARIANT/src/"
    for f in "${FILES[@]}"; do
        cp "BASE_symcts/$f" "$VARIANT/$f"
    done
done
