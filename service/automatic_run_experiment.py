#!/usr/bin/env python3
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""Reads experiment-requests.yaml and determines if an experiment should run and
runs one if necessary. Note that this code uses a config file for experiments
that is not generic. Thus, it only works on the official fuzzbench service. This
script can be run manually but is intended to be run by a cronjob."""
import argparse
import datetime
import os
import sys

import pytz

from common import logs
from common import fuzzer_utils
from common import utils
from common import yaml_utils
from database import models
from database import utils as db_utils
from experiment import run_experiment
from experiment import stop_experiment
from src_analysis import experiment_changes

EXPERIMENT_CONFIG_FILE = os.path.join(utils.ROOT_DIR, 'service',
                                      'experiment-config.yaml')

REQUESTED_EXPERIMENTS_PATH = os.path.join(utils.ROOT_DIR, 'service',
                                          'experiment-requests.yaml')

# TODO(metzman): Stop hardcoding benchmarks and support marking benchmarks as
# disabled using a config file in each benchmark.
BENCHMARKS = [
    # OSS-Fuzz benchmarks.
    'bloaty_fuzz_target',
    'curl_curl_fuzzer_http',
    'jsoncpp_jsoncpp_fuzzer',
    'libpcap_fuzz_both',
    'mbedtls_fuzz_dtlsclient',
    'openssl_x509',
    'sqlite3_ossfuzz',
    'systemd_fuzz-link-parser',
    'zlib_zlib_uncompress_fuzzer',
    'freetype2-2017',
    'harfbuzz-1.3.2',

    # Standard benchmarks.
    'lcms-2017-03-21',
    'libjpeg-turbo-07-2017',
    'libpng-1.2.56',
    'libxml2-v2.9.2',
    'openthread-2019-12-23',
    'proj4-2017-08-14',
    're2-2014-12-09',
    'vorbis-2017-12-11',
    'woff2-2016-05-06',
]


def _get_experiment_name(experiment_config: dict) -> str:
    """Returns the name of the experiment described by experiment_config as a
    string."""
    # Use str because the yaml parser will parse things like `2020-05-06` as
    # a datetime if not included in quotes.
    return str(experiment_config['experiment'])


def run_requested_experiment(dry_run):
    """Run the oldest requested experiment that hasn't been run yet in
    experiment-requests.yaml."""
    requested_experiments = yaml_utils.read(REQUESTED_EXPERIMENTS_PATH)
    requested_experiment = None
    for experiment_config in requested_experiments:
        experiment_name = _get_experiment_name(experiment_config)
        print(str(experiment_name))
        experiment_request_is_new = db_utils.query(models.Experiment).filter(
            models.Experiment.name == experiment_name).first() is None
        if experiment_request_is_new:
            requested_experiment = experiment_config
            break

    if requested_experiment is None:
        logs.info('Not running new experiment.')
        return None

    experiment_name = _get_experiment_name(experiment_config)
    fuzzers = requested_experiment['fuzzers']

    logs.info('Running experiment: %s with fuzzers: %s.',
              experiment_name, ' '.join(fuzzers))
    fuzzer_configs = fuzzer_utils.get_fuzzer_configs(fuzzers=fuzzers)
    return _run_experiment(experiment_name, fuzzer_configs, dry_run)


def _run_experiment(experiment_name, fuzzer_configs, dry_run=False):
    """Run an experiment named |experiment_name| on |fuzzer_configs| and shut it
    down once it terminates."""
    logs.info('Starting experiment: %s.', experiment_name)
    if dry_run:
        logs.info('Dry run. Not actually running experiment.')
        return
    run_experiment.start_experiment(experiment_name, EXPERIMENT_CONFIG_FILE,
                                    BENCHMARKS, fuzzer_configs)
    stop_experiment.stop_experiment(experiment_name, EXPERIMENT_CONFIG_FILE)


def main():
    """Run an experiment."""
    logs.initialize()
    parser = argparse.ArgumentParser(description='Run a requested experiment.')
    # TODO(metzman): Add a way to exit immediately if there is already an
    # experiment running. FuzzBench's scheduler isn't smart enough to deal with
    # this properly.
    parser.add_argument('-d',
                        '--dry-run',
                        help='Dry run, don\'t actually run the experiment',
                        default=False,
                        action='store_true')
    args = parser.parse_args()
    run_requested_experiment(args.dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
