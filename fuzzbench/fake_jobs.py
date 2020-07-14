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
"""Fake jobs."""

import time


def build_image(name):
    """Build a Docker image."""
    print('Building', name)
    time.sleep(3)
    return True


def run_trial():
    """Run a trial."""
    return True


def measure_corpus_snapshot():
    """Measure a corpus snapshot."""
    return True
