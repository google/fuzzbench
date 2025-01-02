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

FUZZERS=(
    symcts_afl_ablation_resource_tracking
    symcts_afl_ablation_resource_tracking_per_branch
)

# 3 largest targets as of https://www.fuzzbench.com/reports/2024-08-23-2028-bases/index.html
TARGETS=(
    sqlite3_ossfuzz     # 20304 max edges
    libxml2_xml         # 15795 max edges
    freetype2_ftfuzzer  # 12025 max edges
)

# 5 runs * 2 fuzzers * 3 benchmarks = 30 trials

EXPERIMENT_NAME="symcts-scale-$(date +%Y%m%d-%H%M%S)"

# --benchmarks libpng-1.2.56
# libpcap_fuzz_both vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer
# --no-seeds \

# use python3.10 if it exists, otherwise use python3.8 if it exists, otherwise use python3
PYTHON3=$(which python3.10 || which python3.8 || which python3)

    # --no-seeds \
    # --no-dictionaries \

PYTHONPATH=. "$PYTHON3" experiment/run_experiment.py \
    --allow-uncommitted-changes \
    --experiment-config symcts_scripts/symcts_experiment_config_ablations_batch.yaml \
    --concurrent-builds 4 \
    --runners-cpus 35 \
    --measurers-cpus 13 \
    --experiment-name $EXPERIMENT_NAME \
    --fuzzers "${FUZZERS[@]}" \
    --benchmarks "${TARGETS[@]}" \
