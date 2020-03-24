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
"""Common utilities."""

import hashlib
import os
import urllib.request
import urllib.error

from common import environment

ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

# pylint: disable=invalid-name
_is_local = None

if os.getenv('FORCE_NOT_LOCAL'):
    # Allow local users to force is_local to return False. This allows things
    # like stackdriver logging to happen when running code locally.
    _is_local = False

if os.getenv('FORCE_LOCAL'):
    _is_local = True


def is_local():
    """Returns True if called on a local development machine.
    Returns False if called on Google Cloud."""
    global _is_local  # pylint: disable=invalid-name

    if _is_local is not None:
        return _is_local
    try:
        # TODO(github.com/google/fuzzbench/issues/82): Get rid of this.
        urllib.request.urlopen('http://metadata.google.internal')
        _is_local = False
    except urllib.error.URLError:
        _is_local = True
    return _is_local


def is_local_experiment():
    """Returns True if running a local experiment."""
    return bool(environment.get('LOCAL_EXPERIMENT'))


def string_hash(obj):
    """Returns a SHA-1 hash of the object. Not used for security purposes."""
    return hashlib.sha1(str(obj).encode('utf-8')).hexdigest()


def file_hash(file_path):
    """Returns the SHA-1 hash of |file_path| contents."""
    chunk_size = 51200  # Read in 50 KB chunks.
    digest = hashlib.sha1()
    with open(file_path, 'rb') as file_handle:
        chunk = file_handle.read(chunk_size)
        while chunk:
            digest.update(chunk)
            chunk = file_handle.read(chunk_size)

    return digest.hexdigest()
