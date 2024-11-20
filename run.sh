#!/bin/bash

# Check if both arguments are provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <experiment_name> <fuzzers>"
    exit 1
fi

EXPERIMENT_NAME=$1
FUZZERS=$2

PYTHONPATH=. python3 experiment/run_experiment.py \
--experiment-config service/experiment-config.yaml \
--benchmarks "bloaty_fuzz_target" "freetype2_ftfuzzer" "harfbuzz_hb-shape-fuzzer" "lcms_cms_transform_fuzzer" "libjpeg-turbo_libjpeg_turbo_fuzzer" "libpcap_fuzz_both" "libxml2_xml" "libxslt_xpath" "mbedtls_fuzz_dtlsclient" \
--experiment-name "$EXPERIMENT_NAME" \
--fuzzers "$FUZZERS"
