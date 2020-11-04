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

import os

from clusterfuzz import stacktraces

from common import logs
from common import new_process
from common import sanitizer

logger = logs.Logger('run_crashes')

# Memory limit for libfuzzer merge.
RSS_LIMIT_MB = 2048

# Per-unit processing timeout for libfuzzer crash.
UNIT_TIMEOUT = 10


def process_crash(app_binary, crash_testcase_path):
    """Returns the crashing unit in coverage_binary_output."""
    # Run the crash with sanitizer options set in environment.
    env = os.environ.copy()
    sanitizer.set_sanitizer_options(env)
    command = [
        app_binary,
        '-timeout=%d' % UNIT_TIMEOUT,
        '-rss_limit_mb=%d' % RSS_LIMIT_MB, crash_testcase_path
    ]
    app_binary_dir = os.path.dirname(app_binary)
    result = new_process.execute(command,
                                 env=env,
                                 cwd=app_binary_dir,
                                 expect_zero=False,
                                 kill_children=True,
                                 timeout=UNIT_TIMEOUT + 5)
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
    return crash_result


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
            crash_result = process_crash(app_binary, crash_testcase_path)
            if crash_result:
                crash_key = _get_crash_key(crash_result)
                crashes[crash_key] = {
                    'crash_testcase': filename,
                    'crash_type': crash_result.crash_type,
                    'crash_address': crash_result.crash_address,
                    'crash_state': crash_result.crash_state,
                    'crash_stacktrace': crash_result.crash_stacktrace,
                }
    return crashes
