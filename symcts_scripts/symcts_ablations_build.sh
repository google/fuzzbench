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

#!/bin/bash
FUZZERS=()
FUZZERS+=(
    symcc_aflplusplus
    symcts_afl
)
FUZZERS+=(
    # symcts_afl_ablation_scheduling_symcc
    # symcts_afl_ablation_coverage_edge_coverage
    # symcts_afl_ablation_mutation_full_solve_first
    # symcts_afl_ablation_sync_always_sync
    # symcts_afl_ablation_symcts_as_symcc
    # symcts_afl_ablation_resource_tracking
    # symcts_afl_ablation_resource_tracking_per_branch
)

TARGETS=(
    bloaty_fuzz_target
    libxml2_xml
    sqlite3_ossfuzz
    openh264_decoder_fuzzer
    stb_stbi_read_fuzzer
)


MAKEFILETARGETS=()

for target in ${TARGETS[@]}
do
    MAKEFILETARGETS+=(build-coverage-$target)
    for fuzzer in ${FUZZERS[@]}
    do
        if [ "$fuzzer" = "symcc_aflplusplus" ] && [ "$target" = "sqlite3_ossfuzz" ]; then
            echo "Skipping symcc_aflplusplus for sqlite3_ossfuzz"
        else
            MAKEFILETARGETS+=(build-$fuzzer-$target .$fuzzer-$target-runner .coverage-$target-builder)
        fi
    done
done

echo ${MAKEFILETARGETS[@]}
make ${MAKEFILETARGETS[@]} -j8 -k
