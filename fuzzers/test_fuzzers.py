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
"""Tests for fuzzers/."""
import importlib

import pytest

from common import fuzzer_utils

# pylint: disable=invalid-name,unused-argument


def _get_fuzzer_module(fuzzer):
    """Get the module for |fuzzer|'s fuzzer.py."""
    return 'fuzzers.{}.fuzzer'.format(fuzzer)


def _get_all_fuzzer_modules():
    """Returns the fuzzer.py modules for all fuzzers."""
    fuzzers = fuzzer_utils.get_all_fuzzers()
    return [
        importlib.import_module(_get_fuzzer_module(fuzzer))
        for fuzzer in fuzzers
    ]


@pytest.mark.parametrize('fuzzer_module', _get_all_fuzzer_modules())
def test_build_function_errors(fuzzer_module, fs):
    """Test that calling the build function will cause an error when
    the benchmark can't be built. Test also ensures that there are no
    type errors which can be made by having the wrong signature."""
    with pytest.raises(Exception) as error:
        fuzzer_module.build()

    # Type error probably means module is doing something else wrong,
    # so fail if we see one. If that is not the case than this assert
    # should be removed.
    assert not isinstance(error.value, TypeError)


@pytest.mark.parametrize('fuzzer_module', _get_all_fuzzer_modules())
def test_fuzz_function_errors(fuzzer_module, fs):
    """Test that calling the fuzz function will cause an error when
    the benchmark can't be built. Test also ensures that there are no
    type errors which can be made by having the wrong signature.
    This test is needed to that make .test-run-$fuzzer-$benchmark
    fails when it is supposed to."""

    with pytest.raises(Exception) as error:
        fuzzer_module.fuzz('/input-corpus', '/output-corpus', '/target-binary')

    # Type error probably means module is doing something else wrong,
    # so fail if we see one. If that is not the case than this assert
    # should be removed.
    assert not isinstance(error.value, TypeError)
