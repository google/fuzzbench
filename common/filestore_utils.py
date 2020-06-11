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

import functools

from common import experiment_utils

#pylint: disable=invalid-name,global-at-module-level,redefined-outer-name,import-outside-toplevel


def _using_gsutil():
    """Returns True if using Google Cloud Storage for filestore."""
    try:
        experiment_filestore_path = (
            experiment_utils.get_experiment_filestore_path())
    except KeyError:
        return True

    return experiment_filestore_path.startswith('gs://')


global filestore_utils_impl
filestore_utils_impl = None


def get_filestore_utils_impl():
    """Imports filestore_utils_impl dynamically."""

    def wrap(func):
        """Helps decorate function |func|."""

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            """Switches to desired filestore_utils_impl accordingly."""
            if _using_gsutil():
                global filestore_utils_impl
                from common import gsutil as filestore_utils_impl
            else:
                # Use local_filestore when not using gsutil.
                global filestore_utils_impl
                from common import local_filestore as filestore_utils_impl
            return func(*args, **kwargs)

        return wrapper

    return wrap


@get_filestore_utils_impl()
def cp(source, destination, recursive=False, parallel=False):  # pylint: disable=invalid-name
    """Copies |source| to |destination|."""
    return filestore_utils_impl.cp(source,
                                   destination,
                                   recursive=recursive,
                                   parallel=parallel)


@get_filestore_utils_impl()
def ls(path, must_exist=True):  # pylint: disable=invalid-name
    """Lists files or folders in |path|. If |must_exist|
    is True then it can raise subprocess.CalledProcessError."""
    return filestore_utils_impl.ls(path, must_exist=must_exist)


@get_filestore_utils_impl()
def rm(path, recursive=True, force=False, parallel=False):  # pylint: disable=invalid-name
    """Removes |path|."""
    return filestore_utils_impl.rm(path,
                                   recursive=recursive,
                                   force=force,
                                   parallel=parallel)


@get_filestore_utils_impl()
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
