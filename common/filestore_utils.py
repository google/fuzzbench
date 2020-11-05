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
"""Helper functions for interacting with the file storage."""

from common import experiment_utils
from common import gsutil
from common import local_filestore


def _using_gsutil():
    """Returns True if using Google Cloud Storage for filestore."""
    try:
        experiment_filestore_path = (
            experiment_utils.get_experiment_filestore_path())
    except KeyError:
        return True

    return experiment_filestore_path.startswith('gs://')


def get_impl():
    """Returns the implementation for filestore_utils."""
    if _using_gsutil():
        return gsutil
    # Use local_filestore when not using gsutil.
    return local_filestore


def cp(source, destination, recursive=False, expect_zero=True, parallel=False):  # pylint: disable=invalid-name
    """Copies |source| to |destination|. If |expect_zero| is True then it can
    raise subprocess.CalledProcessError. |parallel| is only used by the gsutil
    implementation."""
    return get_impl().cp(source,
                         destination,
                         recursive=recursive,
                         expect_zero=expect_zero,
                         parallel=parallel)


def ls(path, must_exist=True):  # pylint: disable=invalid-name
    """Lists files or folders in |path| as one filename per line.
    If |must_exist| is True then it can raise subprocess.CalledProcessError."""
    return get_impl().ls(path, must_exist=must_exist)


def rm(path, recursive=True, force=False, parallel=False):  # pylint: disable=invalid-name
    """Removes |path|."""
    return get_impl().rm(path,
                         recursive=recursive,
                         force=force,
                         parallel=parallel)


def rsync(  # pylint: disable=too-many-arguments
        source,
        destination,
        delete=True,
        recursive=True,
        gsutil_options=None,
        options=None,
        parallel=False):
    """Syncs |source| and |destination| folders. |gsutil_options| and |parallel|
    are only used by the gsutil implementation."""
    return get_impl().rsync(source,
                            destination,
                            delete,
                            recursive,
                            gsutil_options,
                            options,
                            parallel=parallel)


def cat(file_path, expect_zero=True):
    """Reads the file at |file_path| and returns the result."""
    return get_impl().cat(file_path, expect_zero=expect_zero)
