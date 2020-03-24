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
"""Tests for utils.py."""

import os
import pytest

from fuzzers import utils

# pylint: disable=invalid-name,unused-argument


def test_no_dictionary(fs):
    """Test that None is returned when no dictionary is found."""
    assert utils.get_dictionary_path('/fuzz-target') is None


def test_dictionary_dict_file(fs):
    """Test that target.dict file is returned when it exists."""
    fs.create_file('/fuzz-target.dict', contents='A')
    assert utils.get_dictionary_path('/fuzz-target') == '/fuzz-target.dict'


def test_dictionary_bad_options_file(fs):
    """Test that Exception is returned when options file cannot be parsed."""
    fs.create_file('/fuzz-target.options', contents=']')
    with pytest.raises(Exception):
        utils.get_dictionary_path('/fuzz-target')


def test_dictionary_options_file_with_no_dict(fs):
    """Test that None is returned when options file has not dict attribute."""
    fs.create_file('/fuzz-target.options', contents='[test]')
    assert utils.get_dictionary_path('/fuzz-target') is None


def test_dictionary_options_file_with_nonexistent_dict(fs):
    """Test that ValueError is returned when options file's dict attribute
    contains a dict that is invalid / does not exist."""
    fs.create_file('/fuzz-target.options',
                   contents='[test]\ndict = not_exist.dict')
    with pytest.raises(ValueError):
        utils.get_dictionary_path('/fuzz-target')


def test_dictionary_options_file_with_dict(fs):
    """Test that dictionary path is returned when options file has a valid
    dict attribute."""
    fs.create_file('/fuzz.dict', contents='A')
    fs.create_file('/fuzz-target.options', contents='[test]\ndict = fuzz.dict')
    assert utils.get_dictionary_path('/fuzz-target') == '/fuzz.dict'


def test_dictionary_skip(fs, environ):
    """Test that None is return when SKIP_DICT is set."""
    os.environ['SKIP_DICT'] = '1'
    fs.create_file('/fuzz-target.dict', contents='A')
    assert utils.get_dictionary_path('/fuzz-target') is None
