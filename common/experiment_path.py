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
"""Helper functions for paths used in the experiment."""
from pathlib import Path
from common import experiment_utils

# pathlib.Path cannot be inherited from, so use a module instead of a subclass.


def path(*path_segments) -> Path:
    """Returns a Path starting with |path_segements| relative to WORK_DIR."""
    return Path(experiment_utils.get_work_dir(), *path_segments)


def filestore(path_obj: Path) -> str:
    """Returns a string with WORK_DIR replaced with |experiment_filestore_path|.
    |path_obj| should be created by path()."""
    path_str = str(path_obj)
    work_dir = experiment_utils.get_work_dir()
    experiment_filestore_path = experiment_utils.get_experiment_filestore_path()
    assert path_str.startswith(work_dir)
    return path_str.replace(work_dir, experiment_filestore_path)
