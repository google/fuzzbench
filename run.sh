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
--benchmarks "openh264_decoder_fuzzer" "openssl_x509" "openthread_ot-ip6-send-fuzzer" "proj4_proj_crs_to_crs_fuzzer" "re2_fuzzer" "sqlite3_ossfuzz" "stb_stbi_read_fuzzer" "systemd_fuzz-link-parser" "vorbis_decode_fuzzer" \
--experiment-name "$EXPERIMENT_NAME" \
--fuzzers "$FUZZERS"
