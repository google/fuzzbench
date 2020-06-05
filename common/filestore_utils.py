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

from common import logs
from common import experiment_utils

logger = logs.Logger('filestore_utils')


def _using_gsutil():
    """Returns True if using Google Cloud Storage for filestore."""
    try:
        experiment_path_format = experiment_utils.get_experiment_filestore_path(
        )
    except KeyError:
        return True

    return experiment_path_format.startswith('gs://')


if _using_gsutil():
    from common import gsutil as filestore_utils_impl
else:
    # When gsutil is not used in the context, here it should use local_utils.
    # TODO(zhichengcai): local_utils
    from common import gsutil as filestore_utils_impl


def cp(*cp_arguments, **kwargs):  # pylint: disable=invalid-name
    """Copy source to destination."""
    return filestore_utils_impl.cp(*cp_arguments, **kwargs)


def ls(*ls_arguments, must_exist=True, **kwargs):  # pylint: disable=invalid-name
    """List files or folders."""
    return filestore_utils_impl.ls(*ls_arguments, must_exist, **kwargs)


def rm(*rm_arguments, recursive=True, force=False, **kwargs):  # pylint: disable=invalid-name
    """Remove files or folders."""
    return filestore_utils_impl.rm(*rm_arguments, recursive, force, **kwargs)


def rsync(  # pylint: disable=too-many-arguments
        source,
        destination,
        delete=True,
        recursive=True,
        gsutil_options=None,
        options=None,
        **kwargs):
    """Synchronize source and destination folders."""
    return filestore_utils_impl.rsync(source, destination, delete, recursive,
                                      gsutil_options, options, **kwargs)
