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
"""Reads experiment-requests.yaml and determines if there is a new experiment
and runs it if needed. Note that this code uses a config file for experiments
that is specific to the FuzzBench service. Therefore this code will break if
others try to run it."""
import argparse
import collections
import os
import re
import sys
from typing import Optional

from common import benchmark_utils
from common import logs
from common import utils
from common import yaml_utils
from database import models
from database import utils as db_utils
from experiment import run_experiment

logger = logs.Logger('automatic_run_experiment')  # pylint: disable=invalid-name

EXPERIMENT_CONFIG_FILE = os.path.join(utils.ROOT_DIR, 'service',
                                      'experiment-config.yaml')

REQUESTED_EXPERIMENTS_PATH = os.path.join(utils.ROOT_DIR, 'service',
                                          'experiment-requests.yaml')

# Don't run an experiment if we have a "request" just containing this keyword.
# TODO(metzman): Look into replacing this mechanism for pausing the service.
PAUSE_SERVICE_KEYWORD = 'PAUSE_SERVICE'

EXPERIMENT_NAME_REGEX = re.compile(r'^\d{4}-\d{2}-\d{2}.*')


def _get_experiment_name(experiment_config: dict) -> str:
    """Returns the name of the experiment described by |experiment_config| as a
    string."""
    # Use str because the yaml parser will parse things like `2020-05-06` as
    # a datetime if not included in quotes.
    return str(experiment_config['experiment'])


def _get_description(experiment_config: dict) -> Optional[str]:
    """Returns the description of the experiment described by
    |experiment_config| as a string."""
    return experiment_config.get('description')


def _use_oss_fuzz_corpus(experiment_config: dict) -> bool:
    """Returns the oss_fuzz_corpus flag of the experiment described by
    |experiment_config| as a bool."""
    return bool(experiment_config.get('oss_fuzz_corpus'))


def _get_requested_experiments():
    """Return requested experiments."""
    return yaml_utils.read(REQUESTED_EXPERIMENTS_PATH)


def validate_experiment_name(experiment_name):
    """Returns True if |experiment_name| is valid."""
    if EXPERIMENT_NAME_REGEX.match(experiment_name) is None:
        logger.error('Experiment name: %s is not valid.', experiment_name)
        return False
    try:
        run_experiment.validate_experiment_name(experiment_name)
        return True
    except run_experiment.ValidationError:
        logger.error('Experiment name: %s is not valid.', experiment_name)
        return False


def _validate_individual_experiment_requests(experiment_requests):
    """Returns True if all requests in |experiment_request| are valid in
    isolation. Does not account for PAUSE_SERVICE_KEYWORD or duplicates."""
    valid = True
    # Validate format.
    for request in experiment_requests:
        if not isinstance(request, dict):
            logger.error('Request: %s is not a dict.', request)
            experiment_requests.remove(request)
            valid = False
            continue

        if 'experiment' not in request:
            logger.error('Request: %s does not have field "experiment".',
                         request)
            valid = False
            continue

        experiment = _get_experiment_name(request)
        if not validate_experiment_name(experiment):
            valid = False
            # Request isn't so malformed that we can find other issues, if
            # present.

        fuzzers = request.get('fuzzers')
        if not fuzzers:
            logger.error('Request: %s does not specify any fuzzers.', request)
            valid = False
            continue

        for fuzzer in fuzzers:
            try:
                run_experiment.validate_fuzzer(fuzzer)
            except run_experiment.ValidationError:
                logger.error('Fuzzer: %s is invalid.', fuzzer)
                valid = False

        description = request.get('description')
        if description is not None and not isinstance(description, str):
            logger.error(
                'Request: %s "description" attribute is not a valid string.',
                request)
            valid = False

        oss_fuzz_corpus = request.get('oss_fuzz_corpus')
        if oss_fuzz_corpus is not None and not isinstance(
                oss_fuzz_corpus, bool):
            logger.error(
                'Request: %s "oss_fuzz_corpus" attribute is not a valid bool.',
                request)
            valid = False

        experiment_type = request.get('type',
                                      benchmark_utils.BenchmarkType.CODE.value)
        if experiment_type not in benchmark_utils.BENCHMARK_TYPE_STRS:
            logger.error('Type: %s is invalid, must be one of %s',
                         experiment_type, benchmark_utils.BENCHMARK_TYPE_STRS)
            valid = False

    return valid


def validate_experiment_requests(experiment_requests):
    """Returns True if all requests in |experiment_requests| are valid."""
    # This function tries to find as many requests as possible.
    if PAUSE_SERVICE_KEYWORD in experiment_requests:
        # This is a special case where a string is used instead of an experiment
        # to tell the service not to run experiments automatically. Remove it
        # from the list because it fails validation.
        experiment_requests = experiment_requests[:]  # Don't mutate input.
        experiment_requests.remove(PAUSE_SERVICE_KEYWORD)

    if not _validate_individual_experiment_requests(experiment_requests):
        # Don't try the next validation step if the previous failed, we might
        # exception.
        return False

    # Make sure experiment requests have a unique name, we can't run the same
    # experiment twice.
    counts = collections.Counter(
        [request['experiment'] for request in experiment_requests])

    valid = True
    for experiment_name, count in counts.items():
        if count != 1:
            logger.error('Experiment: "%s" appears %d times.',
                         str(experiment_name), count)
            valid = False

    return valid


def run_requested_experiment(dry_run):
    """Run the oldest requested experiment that hasn't been run yet in
    experiment-requests.yaml."""
    requested_experiments = _get_requested_experiments()

    # TODO(metzman): Look into supporting benchmarks as an optional parameter so
    # that people can add fuzzers that don't support everything.

    if PAUSE_SERVICE_KEYWORD in requested_experiments:
        # Check if automated experiment service is paused.
        logs.warning('Pause service requested, not running experiment.')
        return

    requested_experiment = None
    for experiment_config in reversed(requested_experiments):
        experiment_name = _get_experiment_name(experiment_config)
        with db_utils.session_scope() as session:
            is_new_experiment = session.query(models.Experiment).filter(
                models.Experiment.name == experiment_name).first() is None
        if is_new_experiment:
            requested_experiment = experiment_config
            break

    if requested_experiment is None:
        logs.info('No new experiment to run. Exiting.')
        return

    experiment_name = _get_experiment_name(requested_experiment)
    if not validate_experiment_requests([requested_experiment]):
        logs.error('Requested experiment: %s in %s is not valid.',
                   requested_experiment, REQUESTED_EXPERIMENTS_PATH)
        return
    fuzzers = requested_experiment['fuzzers']

    benchmark_type = requested_experiment.get('type')
    if benchmark_type == benchmark_utils.BenchmarkType.BUG.value:
        valid_benchmarks = benchmark_utils.exclude_non_cpp(
            benchmark_utils.get_bug_benchmarks())
    else:
        valid_benchmarks = benchmark_utils.exclude_non_cpp(
            benchmark_utils.get_coverage_benchmarks())

    benchmarks = requested_experiment.get('benchmarks')
    if benchmarks is None:
        benchmarks = valid_benchmarks
    else:
        errors = False
        for benchmark in benchmarks:
            if benchmark not in valid_benchmarks:
                logs.error(
                    'Requested experiment:'
                    ' in %s, %s is not a valid %s benchmark.',
                    requested_experiment, benchmark, benchmark_type)
                errors = True
        if errors:
            return

    logs.info('Running experiment: %s with fuzzers: %s.', experiment_name,
              ' '.join(fuzzers))
    description = _get_description(requested_experiment)
    oss_fuzz_corpus = _use_oss_fuzz_corpus(requested_experiment)
    _run_experiment(experiment_name, fuzzers, benchmarks, description,
                    oss_fuzz_corpus, dry_run)


def _run_experiment(  # pylint: disable=too-many-arguments
        experiment_name,
        fuzzers,
        benchmarks,
        description,
        oss_fuzz_corpus,
        dry_run=False):
    """Run an experiment named |experiment_name| on |fuzzer_configs| and shut it
    down once it terminates."""
    logs.info('Starting experiment: %s.', experiment_name)
    if dry_run:
        logs.info('Dry run. Not actually running experiment.')
        return
    run_experiment.start_experiment(experiment_name,
                                    EXPERIMENT_CONFIG_FILE,
                                    benchmarks,
                                    fuzzers,
                                    description=description,
                                    oss_fuzz_corpus=oss_fuzz_corpus)


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
    try:
        run_requested_experiment(args.dry_run)
    except Exception:  # pylint: disable=broad-except
        logger.error('Error running requested experiment.')
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
