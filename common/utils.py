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
import http.client
import os
import urllib.request
import urllib.error

ROOT_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))

assert not (os.getenv('FORCE_NOT_LOCAL') and os.getenv('FORCE_LOCAL')), (
    'You can\'t set FORCE_LOCAL and FORCE_NOT_LOCAL environment variables to '
    'True at the same time. If you haven\'t set either of these and/or don\'t '
    'understand why this is happening please file a bug.')

# pylint: disable=invalid-name
_is_local = None

if os.getenv('FORCE_NOT_LOCAL'):
    # Allow local users to force is_local to return False. This allows things
    # like logging to happen when running code locally.
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
    except http.client.RemoteDisconnected:
        _is_local = True
    return _is_local


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
