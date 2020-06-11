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
import os
import importlib

from pyfakefs.fake_filesystem_unittest import Patcher
import pytest

from common import utils

# pylint: disable=invalid-name,unused-argument
FUZZER_BLACKLIST = {'coverage', 'coverage_source_based'}


def get_all_fuzzer_dirs():
    """Returns the list of all fuzzers."""
    fuzzers_dir = os.path.join(utils.ROOT_DIR, 'fuzzers')
    return [
        fuzzer for fuzzer in os.listdir(fuzzers_dir)
        if (os.path.isfile(os.path.join(fuzzers_dir, fuzzer, 'fuzzer.py')) and
            fuzzer not in FUZZER_BLACKLIST)
    ]


def _get_fuzzer_module(fuzzer):
    """Get the module for |fuzzer|'s fuzzer.py."""
    return 'fuzzers.{}.fuzzer'.format(fuzzer)


def _get_all_fuzzer_modules():
    """Returns the fuzzer.py modules for all fuzzers."""
    return [
        importlib.import_module(_get_fuzzer_module(fuzzer))
        for fuzzer in get_all_fuzzer_dirs()
    ]


def test_build_function_errors():
    """This test calls fuzzer_module.build() under circumstances in
    which it should throw an exception. If the call exceptions, the
    test passes, otherwise the test fails. This ensures that we can
    properly detect build failures."""
    for fuzzer_module in _get_all_fuzzer_modules():
        with pytest.raises(Exception) as error, Patcher():
            fuzzer_module.build()

        # Type error probably means module is doing something else
        # wrong, so fail if we see one. If that is not the case than
        # this assert should be removed.
        assert not isinstance(error.value, TypeError)


def test_fuzz_function_errors():
    """This test calls fuzzer_module.fuzz() under circumstances in
    which it should throw an exception. If the call exceptions, the
    test passes, otherwise the test fails. This ensures that we can
    properly detect failures during fuzzing."""
    for fuzzer_module in _get_all_fuzzer_modules():
        with pytest.raises(Exception) as error, Patcher():
            fuzzer_module.fuzz('/input-corpus', '/output-corpus',
                               '/target-binary')

        # Type error probably means module is doing something else wrong,
        # so fail if we see one. If that is not the case than this assert
        # should be removed.
        assert not isinstance(error.value, TypeError)
