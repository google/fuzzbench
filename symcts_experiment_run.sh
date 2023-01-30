#!/bin/bash

EXPERIMENT_NAME="symcts-$(date +%Y%m%d-%H%M%S)"

# --benchmarks libpng-1.2.56
# libpcap_fuzz_both vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer
    # --no-seeds \
    # --concurrent-builds 8 \
PYTHONPATH=. python3.10 experiment/run_experiment.py \
    --allow-uncommitted-changes \
    --experiment-config symcts_experiment_config.yaml \
    --benchmarks libxml2-v2.9.2 libpng-1.6.38 \
    --experiment-name $EXPERIMENT_NAME \
    --fuzzers aflplusplus symcts