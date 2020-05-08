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
"""Tests for filesystem.py."""

import os

import pytest

from common import filesystem

SOURCE_DIR = 'src'
DESTINATION_DIR = 'dst'

# pylint: disable=invalid-name,unused-argument


def test_recreate_directory_existing(fs):
    """Tests that recreate_directory recreates a directory that already
    exists."""
    new_directory = 'new-directory'
    os.mkdir(new_directory)
    new_file = os.path.join(new_directory, 'file')
    with open(new_file, 'w') as file_handle:
        file_handle.write('hi')

    filesystem.recreate_directory(new_directory)
    assert os.path.exists(new_directory)
    assert not os.path.exists(new_file)


def test_recreate_directory_not_existing(fs):
    """Tests that recreate_directory creates a directory that does not already
    exist."""
    new_directory = 'new-directory'
    filesystem.recreate_directory(new_directory)
    assert os.path.exists(new_directory)


def test_copy_nonexistent(fs):
    """Test that copy raises an exception (when appropriate) if asked to copy a
    nonexistent path."""
    # Doesn't throw exception if works properly.
    filesystem.copy('fake1', 'fake2', ignore_errors=True)
    with pytest.raises(FileNotFoundError):
        filesystem.copy('fake1', 'fake2')


def test_copy(fs):
    """Test that copy copies a file."""
    # Doesn't throw exception if works properly.
    src = 'filename'
    contents = 'hi'
    fs.create_file(src, contents=contents)
    dst = 'destination_file'
    filesystem.copy(src, dst, ignore_errors=True)
    assert os.path.exists(dst)
    with open(dst) as file_handle:
        assert file_handle.read() == contents


def test_copytree_nonexistent_source(fs):
    """Test that copytree raises an exception if asked to copy from a
    nonexistent source directory."""
    with pytest.raises(NotADirectoryError):
        filesystem.copytree('fake1', 'fake2')


def test_copytree_file_source(fs):
    """Test that copytree raises an exception if asked to copy from
    a source directory that is really a file."""
    filename = 'file'
    fs.create_file(filename)
    with pytest.raises(NotADirectoryError):
        filesystem.copytree(filename, 'fake2')


def test_copytree_existing_destination(fs):
    """Test that copytree raises an exception if asked to copy to an existing
    destination."""
    fs.create_dir(SOURCE_DIR)
    fs.create_dir(DESTINATION_DIR)
    with pytest.raises(FileExistsError):
        filesystem.copytree(SOURCE_DIR, DESTINATION_DIR)


def test_copytree_empty_dir(fs):
    """Test that copytree can copy an empty directory"""
    fs.create_dir(SOURCE_DIR)
    filesystem.copytree(SOURCE_DIR, DESTINATION_DIR)
    assert os.listdir(DESTINATION_DIR) == []


def test_copytree_dir_with_files(fs):
    """Test that copytree can copy a directory containing files."""
    _create_source_dir(SOURCE_DIR, fs)
    filesystem.copytree(SOURCE_DIR, DESTINATION_DIR)
    _assert_has_source_dir_contents(DESTINATION_DIR)


def test_copytree_dir_subdir_with_files(fs):
    """Test that copytree can copy a directory containing files and a
    subdirectory containing files."""
    _create_source_dir(SOURCE_DIR, fs)
    subdir_name = 'subdir'
    _create_source_dir(os.path.join(SOURCE_DIR, subdir_name), fs)
    filesystem.copytree(SOURCE_DIR, DESTINATION_DIR)
    _assert_has_source_dir_contents(DESTINATION_DIR)
    _assert_has_source_dir_contents(os.path.join(DESTINATION_DIR, subdir_name))


def test_replace_dir_nonexistent_source(fs):
    """Test that replace_dir raises an exception if asked to use a nonexistent
    directory as a source."""
    with pytest.raises(NotADirectoryError):
        filesystem.replace_dir('fake-src', 'dst')


def test_replace_dir_file_source(fs):
    """Test that replace_dir raises an exception if asked to use a file as a
    source directory."""
    filename = 'file'
    fs.create_file(filename)
    with pytest.raises(NotADirectoryError):
        filesystem.replace_dir(filename, 'dst')


def _create_source_dir(src_dir, fs):
    """Create a directory at |src_dir| with some sample files."""
    for idx in range(3):
        fs.create_file(os.path.join(src_dir, str(idx)), contents='srcfile')
    return src_dir


def _assert_has_source_dir_contents(directory):
    """Assert that all of the sample files created by _create_source_dir are in
    |directory|."""
    for idx in range(3):
        file_path = os.path.join(directory, str(idx))
        assert os.path.exists(file_path)
        with open(file_path) as file_handle:
            assert file_handle.read() == 'srcfile'


def test_replace_dir_move(fs):
    """Test that replace_dir will move the source to directory to destination
    when instructed."""
    _create_source_dir(SOURCE_DIR, fs)
    os.mkdir(DESTINATION_DIR)
    filesystem.replace_dir(SOURCE_DIR, DESTINATION_DIR, move=True)
    _assert_has_source_dir_contents(DESTINATION_DIR)
    assert not os.path.exists(SOURCE_DIR)


def test_replace_dir_copy(fs):
    """Test that replace_dir will move the source to directory to destination
    when instructed."""
    _create_source_dir(SOURCE_DIR, fs)
    os.mkdir(DESTINATION_DIR)
    filesystem.replace_dir(SOURCE_DIR, DESTINATION_DIR, move=False)
    _assert_has_source_dir_contents(DESTINATION_DIR)
    assert os.path.exists(SOURCE_DIR)


def test_make_dir_copy(fs):
    """Test that make_dir_copy works as intended."""
    _create_source_dir(SOURCE_DIR, fs)
    copy_dir = filesystem.make_dir_copy(SOURCE_DIR)
    _assert_has_source_dir_contents(copy_dir)
    new_filename = 'new-file'
    copied_new_file_path = os.path.join(copy_dir, new_filename)
    assert not os.path.exists(copied_new_file_path)
    with open(os.path.join(SOURCE_DIR, new_filename), 'w') as file_handle:
        file_handle.write('')
    copy_dir = filesystem.make_dir_copy(SOURCE_DIR)
    _assert_has_source_dir_contents(copy_dir)
    assert os.path.exists(copied_new_file_path)


def test_list_files(fs):
    """Tests that list files traverses subdirectories, only returns files, and
    returns absolute paths."""
    base_dir = 'base'
    file1 = os.path.abspath(os.path.join(base_dir, 'file1'))
    fs.create_file(file1)
    file2 = os.path.abspath(os.path.join(base_dir, 'dir1', 'file2'))
    fs.create_file(file2)
    file3 = os.path.abspath(os.path.join(base_dir, 'dir1', 'dir2', 'file3'))
    fs.create_file(file3)
    assert sorted(filesystem.list_files(base_dir)) == sorted(
        [file1, file2, file3])
