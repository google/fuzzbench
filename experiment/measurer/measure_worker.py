# Copyright 2021 Google LLC
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
"""Module for measuring snapshots from trial runners."""
import json
import os
import pathlib
import tarfile
import tempfile
from typing import Set

from common import experiment_path as exp_path
from common import experiment_utils
from common import logs
from common import filestore_utils
from common import filesystem
from common import utils


MEASURED_FILES_STATE_NAME = 'measured-files'

logger = logs.Logger('measure_worker')  # pylint: disable=invalid-name


def extract_corpus(corpus_archive: str, sha_blacklist: Set[str],
                   output_directory: str):
    """Extract a corpus from |corpus_archive| to |output_directory|."""
    pathlib.Path(output_directory).mkdir(exist_ok=True)
    tar = tarfile.open(corpus_archive, 'r:gz')
    for member in tar.getmembers():

        if not member.isfile():
            # We don't care about directory structure. So skip if not a file.
            continue

        member_file_handle = tar.extractfile(member)
        if not member_file_handle:
            logger.info('Failed to get handle to %s', member)
            continue

        member_contents = member_file_handle.read()
        filename = utils.string_hash(member_contents)
        if filename in sha_blacklist:
            continue

        file_path = os.path.join(output_directory, filename)

        if os.path.exists(file_path):
            # Don't write out duplicates in the archive.
            continue

        filesystem.write(file_path, member_contents, 'wb')


class StateFile:
    """A class representing the state of measuring a particular trial on
    particular cycle. Objects of this class are backed by files stored in the
    bucket."""

    def __init__(self, name: str, state_dir: str, cycle: int):
        self.name = name
        self.state_dir = state_dir
        self.cycle = cycle
        self._prev_state = None

    def _get_bucket_cycle_state_file_path(self, cycle: int) -> str:
        """Get the state file path in the bucket."""
        state_file_name = experiment_utils.get_cycle_filename(
            self.name, cycle) + '.json'
        state_file_path = os.path.join(self.state_dir, state_file_name)
        return exp_path.filestore(pathlib.Path(state_file_path))

    def _get_previous_cycle_state(self) -> list:
        """Returns the state from the previous cycle. Returns [] if |self.cycle|
        is 1."""
        if self.cycle == 1:
            return []

        previous_state_file_bucket_path = (
            self._get_bucket_cycle_state_file_path(self.cycle - 1))

        result = filestore_utils.cat(previous_state_file_bucket_path,
                                     expect_zero=False)
        if result.retcode != 0:
            return []

        return json.loads(result.output)

    def get_previous(self):
        """Returns the previous state."""
        if self._prev_state is None:
            self._prev_state = self._get_previous_cycle_state()

        return self._prev_state

    def set_current(self, state):
        """Sets the state for this cycle in the bucket."""
        state_file_bucket_path = self._get_bucket_cycle_state_file_path(
            self.cycle)
        with tempfile.NamedTemporaryFile(mode='w') as temp_file:
            temp_file.write(json.dumps(state))
            temp_file.flush()
            filestore_utils.cp(temp_file.name, state_file_bucket_path)
