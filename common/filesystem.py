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
"""Broadly useful fileystem-related code."""
import os
from pathlib import Path
import shutil


def create_directory(directory):
    """Creates |directory|, including parent directories, if does not exist
    yet."""
    Path(directory).mkdir(parents=True, exist_ok=True)


def is_subpath(path, possible_subpath):
    """Returns True if |possible_subpath| is a subpath of |path|."""
    common_path = os.path.commonpath([path, possible_subpath])
    return common_path == path


def recreate_directory(directory, create_parents=True):
    """Recreates |directory|."""
    shutil.rmtree(directory, ignore_errors=True)
    if create_parents:
        os.makedirs(directory)
    else:
        os.mkdir(directory)


def write(path, contents, open_flags='w'):
    """Opens file at |path| with |open_flags| and writes |contents| to it."""
    with open(path, open_flags) as file_handle:
        return file_handle.write(contents)


def append(path, line):
    """Appends |line| to the file located at |path|."""
    return write(path, line + '\n', 'a')


def read(path, open_flags='r'):
    """Opens file at |path| with |open_flags| reads it and then returns the
    result."""
    with open(path, open_flags) as file_handle:
        return file_handle.read()


def copy(src, dst, ignore_errors=False):
    """Copy a file from |src| to |dst|. Ignore errors while copying if
    |ignore_errors|."""
    try:
        # str for Python3.5
        shutil.copy2(str(src), str(dst))
    except FileNotFoundError as error:
        if not ignore_errors:
            raise error


def copytree(src, dst, ignore_errors=False):
    """Recursively copy |src| to |dst|. Ignore errors if |ignore_errors|.
    |ignore_errors| allows this function to gracefully copy a directory
    while it is being written to, by ignoring any files that are removed during
    the copying process (e.g. if a fuzzer is adding and removing corpus elements
    during the copy."""
    if not os.path.isdir(src):
        raise NotADirectoryError('Not a directory: ' + src)
    if os.path.exists(dst):
        raise FileExistsError('File exists: ' + dst)
    os.makedirs(dst)
    for root, _, filenames in os.walk(src):
        for filename in filenames:
            src_path = os.path.join(root, filename)
            dst_path = dst / Path(os.path.relpath(src_path, src))
            # str() is necessary in Python 3.5.
            dst_directory = os.path.dirname(str(dst_path))
            if not os.path.exists(dst_directory):
                os.makedirs(dst_directory)
            copy(src_path, dst_path, ignore_errors=ignore_errors)


def replace_dir(src_dir, dst_dir, move=True):
    """Replace |dst_dir| with |src_dir|. Move |src_dir| if |move| otherwise copy
    it."""
    if not os.path.isdir(src_dir):
        raise NotADirectoryError(
            'src_dir must be a directory. %s is not a directory.' % src_dir)
    shutil.rmtree(dst_dir, ignore_errors=True)
    if move:
        shutil.move(src_dir, dst_dir)
    else:
        copytree(src_dir, dst_dir, ignore_errors=True)


def make_dir_copy(src_dir):
    """Copy |src_dir| to "|src_dir|-copy" and return its name."""
    dst_dir = src_dir + '-copy'
    replace_dir(src_dir, dst_dir, move=False)
    return dst_dir


def list_files(directory):
    """Returns a list of absolute paths to all files in |directory| and its
    subdirectories."""
    all_files = []
    for (root, _, files) in os.walk(directory):
        for filename in files:
            all_files.append(os.path.abspath(os.path.join(root, filename)))
    return all_files
