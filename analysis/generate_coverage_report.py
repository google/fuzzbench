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
"""Coverage report generator tool."""

import os

from common import logs
from common import filesystem
from experiment import coverage_utils

logger = logs.Logger('generate_coverage_report')


def generate_coverage_report(experiment_names,
                             report_directory,
                             benchmarks=None,
                             fuzzers=None):
    """Generates coverage reports."""
    logger.info('Generating coverage reports.')
    coverage_report_directory = os.path.join(report_directory,
                                             'coverage-reports')
    filesystem.create_directory(coverage_report_directory)
    try:
        # Generate coverage reports for each benchmark.
        coverage_utils.generate_cov_reports(experiment_names, benchmarks,
                                            fuzzers, coverage_report_directory)
    except Exception:  # pylint: disable=broad-except
        logger.error('Failed to generate coverage reports.')

