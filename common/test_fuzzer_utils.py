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
"""Tests for fuzzer_utils.py."""
import pytest

from common import fuzzer_utils

# pylint: disable=invalid-name,unused-argument


def test_not_found_with_fuzzer_name_arg(fs, environ):
    """Test that None is returned when no fuzz target exists and a non-existent
    fuzzer name argument is provided."""
    fs.create_file('/out/empty')
    assert fuzzer_utils.get_fuzz_target_binary('/out', 'fuzz-target') is None


def test_not_found_without_fuzzer_name_arg(fs, environ):
    """Test that None is returned when no fuzz target exists and None fuzzer
    name argument is provided."""
    fs.create_file('/out/empty')
    assert fuzzer_utils.get_fuzz_target_binary('/out', None) is None


def test_found_fuzzer_on_default_path(fs, environ):
    """Test that default fuzz target path is returned if found."""
    fuzz_target_path = '/out/fuzz-target'
    fs.create_file(fuzz_target_path)
    assert fuzzer_utils.get_fuzz_target_binary('/out',
                                               None) == ('/out/fuzz-target')


def test_found_fuzzer_containing_string_with_fuzzer_name_arg(fs, environ):
    """Test that fuzz target with search string is returned, when fuzzer name
    argument is provided."""
    fs.create_file('/out/custom-target', contents='\n\nLLVMFuzzerTestOneInput')
    assert fuzzer_utils.get_fuzz_target_binary(
        '/out', 'custom-target') == ('/out/custom-target')


def test_found_fuzzer_containing_string_without_fuzzer_name_arg(fs, environ):
    """Test that fuzz target with search string is returned, when None fuzzer
    name argument is provided."""
    fs.create_file('/out/custom-target', contents='\n\nLLVMFuzzerTestOneInput')
    assert fuzzer_utils.get_fuzz_target_binary('/out',
                                               None) == ('/out/custom-target')


@pytest.mark.parametrize(('config', 'expected_result'), [
    ({
        'name': 'myvariant',
        'fuzzer': 'myfuzzer'
    }, 'myvariant'),
    ({
        'fuzzer': 'myfuzzer'
    }, 'myfuzzer'),
])
def test_get_fuzzer_from_config(config, expected_result):
    """Test that get_fuzzer_from_config returns the variant for a
    variant and the fuzzer for a non-variant fuzzer."""
    assert fuzzer_utils.get_fuzzer_from_config(config) == expected_result
