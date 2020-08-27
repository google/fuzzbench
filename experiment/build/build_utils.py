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
"""Module for utility code shared by build submodules."""

import tempfile

from common import experiment_path as exp_path
from common import filestore_utils


def store_build_logs(build_config, build_result):
    """Save build results in the build logs bucket."""
    build_output = ('Command returned {retcode}.\nOutput: {output}'.format(
        retcode=build_result.retcode, output=build_result.output))
    with tempfile.NamedTemporaryFile(mode='w') as tmp:
        tmp.write(build_output)
        tmp.flush()

        build_log_filename = build_config + '.txt'
        filestore_utils.cp(
            tmp.name,
            exp_path.filestore(get_build_logs_dir() / build_log_filename))


def get_coverage_binaries_dir():
    """Return coverage binaries directory."""
    return exp_path.path('coverage-binaries')


def get_build_logs_dir():
    """Return build logs directory."""
    return exp_path.path('build-logs')
