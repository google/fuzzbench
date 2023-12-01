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
"""Module for processing crashes."""

import collections
import os
import re

from clusterfuzz import stacktraces

from common import logs
from common import new_process
from common import sanitizer
from experiment.measurer import run_coverage

logger = logs.Logger()

Crash = collections.namedtuple('Crash', [
    'crash_testcase', 'crash_type', 'crash_address', 'crash_state',
    'crash_stacktrace'
])

SIZE_REGEX = re.compile(r'\s([0-9]+|{\*})$', re.DOTALL)
CPLUSPLUS_TEMPLATE_REGEX = re.compile(r'(<[^>]+>|<[^\n]+(?=\n))')


def _filter_crash_type(crash_type):
    """Filters crash type to remove size numbers."""
    return SIZE_REGEX.sub('', crash_type)


def _filter_crash_state(crash_state):
    """Filters crash state to remove simple templates e.g. <int>."""
    return CPLUSPLUS_TEMPLATE_REGEX.sub('', crash_state)


def process_crash(app_binary, crash_testcase_path, crashes_dir):
    """Returns the crashing unit in coverage_binary_output."""
    crash_filename = os.path.basename(crash_testcase_path)
    if (crash_filename.startswith('oom-') or
            crash_filename.startswith('timeout-')):
        # Don't spend time processing ooms and timeouts as these are
        # uninteresting crashes anyway. These are also excluded below, but don't
        # process them in the first place based on filename.
        return None

    # Run the crash with sanitizer options set in environment.
    env = os.environ.copy()
    sanitizer.set_sanitizer_options(env)
    command = [
        app_binary, f'-timeout={run_coverage.UNIT_TIMEOUT}',
        f'-rss_limit_mb={run_coverage.RSS_LIMIT_MB}', crash_testcase_path
    ]
    app_binary_dir = os.path.dirname(app_binary)
    result = new_process.execute(command,
                                 env=env,
                                 cwd=app_binary_dir,
                                 expect_zero=False,
                                 kill_children=True,
                                 timeout=run_coverage.UNIT_TIMEOUT + 5)
    if not result.output:
        # Hang happened, no crash. Bail out.
        return None

    # Process the crash stacktrace from output.
    fuzz_target = os.path.basename(app_binary)
    stack_parser = stacktraces.StackParser(fuzz_target=fuzz_target,
                                           symbolized=True,
                                           detect_ooms_and_hangs=True,
                                           include_ubsan=True)
    crash_result = stack_parser.parse(result.output)
    if not crash_result.crash_state:
        # No crash occurred. Bail out.
        return None

    if crash_result.crash_type in ('Timeout', 'Out-of-memory'):
        # Uninteresting crash types for fuzzer efficacy. Bail out.
        return None

    return Crash(crash_testcase=os.path.relpath(crash_testcase_path,
                                                crashes_dir),
                 crash_type=_filter_crash_type(crash_result.crash_type),
                 crash_address=crash_result.crash_address,
                 crash_state=_filter_crash_state(crash_result.crash_state),
                 crash_stacktrace=crash_result.crash_stacktrace)


def _get_crash_key(crash_result):
    """Return a unique identifier for a crash."""
    return f'{crash_result.crash_type}:{crash_result.crash_state}'


def do_crashes_run(app_binary, crashes_dir):
    """Does a crashes run of |app_binary| on |crashes_dir|. Returns a list of
    unique crashes."""
    crashes = {}
    for root, _, filenames in os.walk(crashes_dir):
        for filename in filenames:
            crash_testcase_path = os.path.join(root, filename)
            crash = process_crash(app_binary, crash_testcase_path, crashes_dir)
            if crash:
                crashes[_get_crash_key(crash)] = crash
    return crashes
