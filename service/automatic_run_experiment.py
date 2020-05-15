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
"""Determines if an experiment should be run and runs one if necessary.
Note that this code uses a config file for experiments that is not generic.
Thus, it only works on the official fuzzbench service. This script can be
run manually but is intended to be run by a cronjob."""
import argparse
import datetime
import os
import sys

import pytz

from common import logs
from common import fuzzer_utils
from common import utils
from experiment import run_experiment
from experiment import stop_experiment
from src_analysis import experiment_changes

EXPERIMENT_CONFIG_FILE = os.path.join(utils.ROOT_DIR, 'service',
                                      'experiment-config.yaml')

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


def get_experiment_name():
    """Returns the name of the experiment to run."""
    timezone = pytz.timezone('America/Los_Angeles')
    time_now = datetime.datetime.now(timezone)
    return time_now.strftime('%Y-%m-%d')


def run_diff_experiment(dry_run):
    """Run a diff experiment. This is an experiment that runs only on
    fuzzers that have changed since the last experiment."""
    fuzzers = experiment_changes.get_fuzzers_changed_since_last()
    logs.info('Running experiment with fuzzers: %s.', ' '.join(fuzzers))
    fuzzer_configs = fuzzer_utils.get_fuzzer_configs(fuzzers=fuzzers)
    return _run_experiment(fuzzer_configs, dry_run)


def _run_experiment(fuzzer_configs, dry_run=False):
    """Run an experiment on |fuzzer_configs| and shut it down once it
    terminates."""
    experiment_name = get_experiment_name()
    logs.info('Starting experiment: %s.', experiment_name)
    if dry_run:
        logs.info('Dry run. Not actually running experiment.')
        return
    run_experiment.start_experiment(experiment_name, EXPERIMENT_CONFIG_FILE,
                                    BENCHMARKS, fuzzer_configs)
    stop_experiment.stop_experiment(experiment_name, EXPERIMENT_CONFIG_FILE)


def run_full_experiment():
    """Run a full experiment."""
    fuzzer_configs = fuzzer_utils.get_fuzzer_configs()
    return _run_experiment(fuzzer_configs)


def main():
    """Run an experiment."""
    logs.initialize()
    parser = argparse.ArgumentParser(
        description='Run a full or diff experiment (if needed).')
    # TODO(metzman): Add a way to exit immediately if there is already an
    # experiment running. FuzzBench's scheduler isn't smart enough to deal with
    # this properly.
    parser.add_argument('experiment_type', choices=['diff', 'full'])
    parser.add_argument('-d',
                        '--dry-run',
                        help='Dry run, don\'t actually run the experiment',
                        default=False,
                        action='store_true')
    args = parser.parse_args()
    if args.experiment_type == 'full':
        run_full_experiment()
    else:
        run_diff_experiment(args.dry_run)
    return 0


if __name__ == '__main__':
    sys.exit(main())
