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
"""Tests for fuzzer_dependencies.py."""
import os
from unittest import mock

import pytest

from common import utils
from common import fuzzer_utils
from src_analysis import fuzzer_dependencies

# pylint: disable=protected-access,import-outside-toplevel

VARIANT = 'myvariant'
FUZZER = 'myfuzzer'
VARIANT_CONFIG = {'name': VARIANT, 'fuzzer': FUZZER}
FUZZER_CONFIG = {'fuzzer': FUZZER}
CONFIGS = [VARIANT_CONFIG, FUZZER_CONFIG]
FUZZER_NAMES_TO_UNDERLYING = {
    fuzzer_utils.get_fuzzer_from_config(config): config['fuzzer']
    for config in CONFIGS
}


def test_get_fuzzer_module_name():
    """Tests that get_fuzzer_module_name returns the correct module."""
    assert fuzzer_dependencies._get_fuzzer_module_name(
        FUZZER) == 'fuzzers.myfuzzer.fuzzer'


def test_is_builtin_module():
    """Tests that is_builtin_module returns the correct result for builtin
    modules and non-builtin modules."""
    import time
    assert fuzzer_dependencies.is_builtin_module(time)
    assert not fuzzer_dependencies.is_builtin_module(fuzzer_dependencies)


@pytest.mark.parametrize(
    ('path', 'expected_result'), [('fuzzers', True), ('fuzzers/afl', True),
                                  ('fuzzers/utils.py', True),
                                  ('fuzzers/afl/fuzzer.py', True),
                                  ('notfuzzers/afl/fuzzer.py', False),
                                  (__file__, False)])
def test_is_fuzzers_subpath(path, expected_result):
    """Tests that is_fuzzers_subpath returns the correct result for paths that
    are subpaths of fuzzers/ and for paths that aren't subpaths of fuzzers/."""
    path = os.path.join(utils.ROOT_DIR, path)
    assert fuzzer_dependencies.is_fuzzers_subpath(path) == expected_result


def test_is_fuzzers_submodule():
    """Tests that is_fuzzer_submodule returns the correct result for modules
    that are submodules of fuzzer and for modules that aren't submodules of
    fuzzer."""
    # We don't do this using parametrize because imports are impractical to do
    # with it.
    from fuzzers import utils as fuzzers_utils
    from fuzzers.afl import fuzzer as afl_fuzzer
    for module, expected_result in [(fuzzers_utils, True), (afl_fuzzer, True),
                                    (fuzzer_dependencies, False)]:
        assert fuzzer_dependencies.is_fuzzers_submodule(
            module) == expected_result


def test_get_fuzzer_dependencies():
    """Tests that get_fuzzer_dependencies returns the corect dependencies for
    a fuzzer."""
    deps = fuzzer_dependencies.get_fuzzer_dependencies('mopt')
    expected_deps = sorted([
        os.path.join(utils.ROOT_DIR, 'fuzzers', 'afl', 'fuzzer.py'),
        os.path.join(utils.ROOT_DIR, 'fuzzers', 'mopt', 'fuzzer.py'),
        os.path.join(utils.ROOT_DIR, 'fuzzers', 'mopt', 'runner.Dockerfile'),
        os.path.join(utils.ROOT_DIR, 'fuzzers', 'mopt', 'builder.Dockerfile'),
        os.path.join(utils.ROOT_DIR, 'fuzzers', 'utils.py'),
    ])
    assert sorted(deps) == expected_deps


def test_get_python_dependencies():
    """Tests that _get_python_dependencies returns the paths of all python
    dependencies of a module (all dependencies that are in fuzzers/, since
    within fuzzbench, dependencies outside of fuzzers/ is forbidden)."""
    from fuzzers.mopt import fuzzer as mopt_fuzzer
    deps = fuzzer_dependencies._get_python_dependencies(mopt_fuzzer)
    expected_deps = sorted([
        os.path.join(utils.ROOT_DIR, 'fuzzers', 'afl', 'fuzzer.py'),
        os.path.join(utils.ROOT_DIR, 'fuzzers', 'mopt', 'fuzzer.py'),
        os.path.join(utils.ROOT_DIR, 'fuzzers', 'utils.py')
    ])
    assert sorted(deps) == expected_deps


@pytest.mark.parametrize(('fuzzer_name', 'expected_underlying_name'),
                         [(FUZZER, FUZZER), (VARIANT, FUZZER)])
def test_get_underlying_fuzzer(fuzzer_name, expected_underlying_name):
    """Tests that get_underlying_fuzzer returns the underlying fuzzer for a
    fuzzer variant and a normal fuzzer."""
    with mock.patch(
            'src_analysis.fuzzer_dependencies.FUZZER_NAMES_TO_UNDERLYING',
            FUZZER_NAMES_TO_UNDERLYING):
        assert fuzzer_dependencies.get_underlying_fuzzer(
            fuzzer_name) == expected_underlying_name


def test_get_files_dependent_fuzzers_afl_fuzzer_py():
    """Tests that the right fuzzer modules are returned by
    get_files_dependent_fuzzers when passed fuzzers/afl/fuzzer.py. Note that
    this test relies on afl/fuzzer.py being a dependency of
    fairfuzz/fuzzer.py."""
    afl_fuzzer_py_path = os.path.join(utils.ROOT_DIR, 'fuzzers', 'afl',
                                      'fuzzer.py')
    dependent_fuzzers = fuzzer_dependencies.get_files_dependent_fuzzers(
        [afl_fuzzer_py_path])
    assert 'fairfuzz' in dependent_fuzzers
    # Ensure that the fuzzer itself is in the list of dependent_fuzzers.
    assert 'afl' in dependent_fuzzers


def test_get_files_dependent_fuzzers_afl_runner_dockerfile():
    """Tests that the right modules are returned by get_files_dependent_fuzzers
    when passed fuzzers/afl/runner.Dockerfile."""
    afl_runner_dockerfile = os.path.join(utils.ROOT_DIR, 'fuzzers', 'afl',
                                         'runner.Dockerfile')

    dependent_fuzzers = fuzzer_dependencies.get_files_dependent_fuzzers(
        [afl_runner_dockerfile])
    assert 'fairfuzz' not in dependent_fuzzers
    # Ensure that the fuzzer itself is in the list of dependent_fuzzers.
    assert 'afl' in dependent_fuzzers


@mock.patch('src_analysis.fuzzer_dependencies.FUZZER_NAMES_TO_UNDERLYING', {
    VARIANT: 'afl',
    'afl': 'afl'
})
@mock.patch('src_analysis.fuzzer_dependencies.FUZZER_CONFIGS', [{
    'name': VARIANT,
    'fuzzer': 'afl'
}, {
    'fuzzer': 'afl'
}])
def test_get_files_dependent_fuzzers_variant():
    """Test that only variants are depndent on variants.yaml."""
    afl_variants_yaml_path = os.path.join(utils.ROOT_DIR, 'fuzzers', 'afl',
                                          'variants.yaml')
    dependent_fuzzers = fuzzer_dependencies.get_files_dependent_fuzzers(
        [afl_variants_yaml_path])
    assert dependent_fuzzers == [VARIANT]
