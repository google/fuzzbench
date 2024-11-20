#!/bin/bash

# Check if both arguments are provided
if [ $# -ne 2 ]; then
    echo "Usage: $0 <experiment_name> <fuzzers>"
    exit 1
fi

EXPERIMENT_NAME=$1
FUZZERS=$2

PYTHONPATH=. python3 experiment/run_experiment.py \
--experiment-config experiment-config.yaml \
--benchmarks freetype2_ftfuzzer bloaty_fuzz_target \
--experiment-name "$EXPERIMENT_NAME" \
--fuzzers "$FUZZERS"
