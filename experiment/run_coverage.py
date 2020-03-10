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
"""Module for running a sancov instrumented binary on a corpus."""
import os
import tempfile
from typing import List

from common import experiment_utils
from common import logs
from common import new_process

logger = logs.Logger('run_coverage')


def find_crashing_units(artifacts_dir: str) -> List[str]:
    """Returns the crashing unit in coverage_binary_output."""
    return [
        # This assumes the artifacts are named {crash,oom,timeout,*}-$SHA1_HASH
        # and that input units are also named with their hash.
        filename.split('-')[1]
        for filename in os.listdir(artifacts_dir)
        if os.path.isfile(os.path.join(artifacts_dir, filename))
    ]


RSS_LIMIT_MB = 2048
UNIT_TIMEOUT = 5
MAX_TOTAL_TIME = experiment_utils.SNAPSHOT_PERIOD


def do_coverage_run(  # pylint: disable=too-many-locals
        coverage_binary: str, new_units_dir: List[str], sancov_dir: str,
        crashes_dir: str) -> List[str]:
    """Does a coverage run of |coverage_binary| on |new_units_dir|. Writes
    sancov files to |sancov_dir|. Returns a list of crashing units."""
    with tempfile.TemporaryDirectory() as merge_dir:
        command = [
            coverage_binary, '-merge=1', '-dump_coverage=1',
            '-artifact_prefix=%s/' % crashes_dir,
            '-timeout=%d' % UNIT_TIMEOUT,
            '-rss_limit_mb=%d' % RSS_LIMIT_MB,
            '-max_total_time=%d' % MAX_TOTAL_TIME, merge_dir, new_units_dir
        ]
        coverage_binary_dir = os.path.dirname(coverage_binary)
        env = os.environ.copy()
        env['UBSAN_OPTIONS'] = 'coverage_dir=%s' % sancov_dir
        result = new_process.execute(command,
                                     env=env,
                                     cwd=coverage_binary_dir,
                                     expect_zero=False,
                                     kill_children=True,
                                     timeout=MAX_TOTAL_TIME)

    if result.retcode != 0:
        logger.error('Coverage run failed.',
                     extras={
                         'coverage_binary': coverage_binary,
                         'output': result.output[-new_process.LOG_LIMIT_FIELD:],
                     })
    return find_crashing_units(crashes_dir)
