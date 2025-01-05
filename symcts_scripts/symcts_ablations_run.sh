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

FUZZERS=(symcc_aflplusplus symcts_afl)
# FUZZERS+=(aflplusplus libafl)
FUZZERS+=(
    symcts_afl_ablation_scheduling_symcc
    symcts_afl_ablation_scheduling_uniform_random
    symcts_afl_ablation_coverage_edge_coverage
    symcts_afl_ablation_mutation_full_solve_first
    symcts_afl_ablation_sync_always_sync
)

TARGETS=(
    bloaty_fuzz_target
    libxml2_xml
    sqlite3_ossfuzz
    openh264_decoder_fuzzer
    stb_stbi_read_fuzzer
)

# 2 runs * 7 fuzzers * 5 benchmarks = 70 runs

EXPERIMENT_NAME="symcts-abl-$(date +%Y%m%d-%H%M%S)"

REPORT_DIR="/nvme/lukas/fuzzbench/symcts_ablations/report-data/experimental/$EXPERIMENT_NAME"
mkdir -p "$REPORT_DIR"
cp fuzzers/symcts_afl/builder.Dockerfile "$REPORT_DIR"

# --benchmarks libpng-1.2.56
# libpcap_fuzz_both vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer
# --no-seeds \

# use python3.10 if it exists, otherwise use python3.8 if it exists, otherwise use python3
PYTHON3=$(which python3.10 || which python3.8 || which python3)

    # --no-seeds \
    # --no-dictionaries \

PYTHONPATH=. "$PYTHON3" experiment/run_experiment.py \
    --allow-uncommitted-changes \
    --experiment-config symcts_scripts/symcts_experiment_config_ablations.yaml \
    --concurrent-builds 4 \
    --runners-cpus 70 \
    --measurers-cpus 26 \
    --experiment-name $EXPERIMENT_NAME \
    --fuzzers "${FUZZERS[@]}" \
    --benchmarks "${TARGETS[@]}" \
