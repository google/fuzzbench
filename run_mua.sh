#! /bin/bash
source .venv/bin/activate

PYTHONPATH=. python3 experiment/run_experiment.py --experiment-config /tmp/experiment_conf.yaml --benchmarks libxml2_xml --experiment-name mua-test-$(date +"%Y%m%d-%H%M%S") -f afl libfuzzer -a
