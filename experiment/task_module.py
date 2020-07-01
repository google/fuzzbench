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
"""Define the module for tasks."""

import time


def build_task(fuzzer="", benchmark=""):
    """Defines a task."""
    with open('/tmp/queue_test/build_' + str(time.time()) + '_' + fuzzer + '_' + benchmark, 'w') as _:
        pass


def run_task(fuzzer="", benchmark=""):
    """Defines a task."""
    with open('/tmp/queue_test/run_' + str(time.time()) + '_' + fuzzer + '_' + benchmark, 'w') as _:
        pass


def measure_task(fuzzer="", benchmark=""):
    """Defines a task."""
    with open('/tmp/queue_test/measure_' + str(time.time()) + '_' + fuzzer + '_' + benchmark, 'w') as _:
        pass
