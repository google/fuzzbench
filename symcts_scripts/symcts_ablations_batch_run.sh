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

set -u

BATCH_NUM=$1

FUZZERS=(symcc_aflplusplus symcts_afl)
FUZZERS+=(
    symcts_afl_ablation_scheduling_symcc
    symcts_afl_ablation_coverage_edge_coverage
    symcts_afl_ablation_mutation_full_solve_first
    symcts_afl_ablation_sync_always_sync
    symcts_afl_ablation_symcts_as_symcc
)

RUNNERS_CPUS=70
MEASURERS_CPUS=26
case $BATCH_NUM in
    1)
        TARGETS=(bloaty_fuzz_target stb_stbi_read_fuzzer )
        EXPERIMENT_NAME="ablt-blty-stbi-$(date +%Y%m%d-%H%M%S)"
        ;;
    2)
        TARGETS=(openh264_decoder_fuzzer sqlite3_ossfuzz)
        EXPERIMENT_NAME="ablt-o264-sqlt-$(date +%Y%m%d-%H%M%S)"
        ;;
    3)
        TARGETS=(libxml2_xml)
        EXPERIMENT_NAME="ablt-lxml-$(date +%Y%m%d-%H%M%S)"
        RUNNERS_CPUS=35
        MEASURERS_CPUS=13
        ;;
esac




# use python3.10 if it exists, otherwise use python3.8 if it exists, otherwise use python3
PYTHON3=$(which python3.10 || which python3)

# 5 instances * 7 fuzzers = 35     * 2 benchmarks = 70 trials, 70 runner-cpus should do all of them in one batch


PYTHONPATH=. "$PYTHON3" experiment/run_experiment.py \
    --allow-uncommitted-changes \
    --experiment-config symcts_scripts/symcts_experiment_config_ablations_batch.yaml \
    --concurrent-builds 1 \
    --runners-cpus "$RUNNERS_CPUS" \
    --measurers-cpus "$MEASURERS_CPUS" \
    --experiment-name $EXPERIMENT_NAME \
    --fuzzers ${FUZZERS[@]} \
    --benchmarks ${TARGETS[@]} \
