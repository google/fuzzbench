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

import argparse
import os
import sys

import pandas as pd

from analysis import data_utils
from analysis import experiment_results
from analysis import plotting
from analysis import queries
from analysis import rendering
from common import filesystem
from common import logs
from experiment import coverage_utils

logger = logs.Logger('generate_coverage_report')


def generate_coverage_report(experiment_names,
                             report_directory,
                             benchmarks=None,
                             fuzzers=None,
                             from_cached_data=False,
                             merge_with_clobber=False,
                             merge_with_clobber_nonprivate=False):

    logger.info('Generating coverage reports.')

    coverage_report_directory = os.path.join(report_directory,
                                             'coverage-reports')
    try:
        if not from_cached_data:
            coverage_utils.fetch_source_files(benchmarks,
                                            coverage_report_directory)
            coverage_utils.fetch_binary_files(benchmarks,
                                            coverage_report_directory)
            coverage_utils.get_profdata_files(experiment_names[0],
                                            benchmarks, fuzzers,
                                            coverage_report_directory)

        # Generate coverage reports for each benchmark.
        coverage_utils.generate_cov_reports(benchmarks, fuzzers,
                                            coverage_report_directory)
    except Exception:  # pylint: disable=broad-except
        logger.error('Failed to generate coverage reports.')
