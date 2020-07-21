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
"""Jobs."""

import os
import subprocess

BASE_TAG = 'gcr.io/fuzzbench'


def build_image(name: str):
    """Builds a Docker image."""
    image_tag = os.path.join(BASE_TAG, name)
    subprocess.run(['docker', 'pull', image_tag], check=True)
    return subprocess.run(
        ['docker', 'build', '--tag', image_tag,
         os.path.join('docker', name)],
        check=True)


def run_trial():
    """Runs a trial."""
    return True


def measure_corpus_snapshot():
    """Measures a corpus snapshot."""
    return True
