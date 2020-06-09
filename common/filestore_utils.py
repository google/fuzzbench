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


def _using_gsutil():
    """Returns True if using Google Cloud Storage for filestore."""
    try:
        experiment_filestore_path = experiment_utils.get_cloud_experiment_path()
    except KeyError:
        return True

    return experiment_filestore_path.startswith('gs://')


if _using_gsutil():
    from common import gsutil as filestore_utils_impl
else:
    # When gsutil is not used in the context, here it should use local_utils.
    # TODO(zhichengcai): Implement local_filestore.py and import it here.
    from common import gsutil as filestore_utils_impl


# TODO(zhichengcai): Change all implementations of cp, ls, and rm to stop using
# special handling of *args. This is error prone now that there are wrappers.
def cp(source, destination, recursive=False, parallel=False):  # pylint: disable=invalid-name
    """Copies |source| to |destination|."""
    return filestore_utils_impl.cp(source,
                                   destination,
                                   recursive=recursive,
                                   parallel=parallel)


def ls(path, must_exist=True):  # pylint: disable=invalid-name
    """Lists files or folders in |path|. Doesn't except on failure if must_exist
    is False otherwise can raise subprocess.CalledProcessError.
    Returns the output of ls split line-by-line (for example ls('directory/')
    returns every file in the directory."""
    return filestore_utils_impl.ls(path, must_exist=must_exist)


def rm(*rm_arguments, recursive=True, force=False, parallel=False):  # pylint: disable=invalid-name
    """Remove files or folders."""
    return filestore_utils_impl.rm(*rm_arguments,
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
    """Syncs |source| and |destination| folders."""
    return filestore_utils_impl.rsync(source,
                                      destination,
                                      delete,
                                      recursive,
                                      gsutil_options,
                                      options,
                                      parallel=parallel)
