#! /bin/bash
source .venv/bin/activate

PYTHONPATH=. python3 experiment/run_experiment.py --experiment-config /home/joschua/Desktop/CISPA/Projekte/SBFT/experiment/config.yaml --benchmarks bloaty_fuzz_target --experiment-name testrun01-fuzzers afl libfuzzer -a

