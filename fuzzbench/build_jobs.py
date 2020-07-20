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
"""Creates build jobs."""

import os
import subprocess
import time

from rq.job import Job


BASE_TAG = 'gcr.io/fuzzbench'


def build_base_images(name):
    """Builds a Docker image."""
    image_tag = os.path.join(BASE_TAG, name)
    return subprocess.run(['docker', 'build',
                    '--tag', image_tag,
                    os.path.join('docker', name)
                    ])
