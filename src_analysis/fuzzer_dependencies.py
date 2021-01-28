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
"""Module for finding dependencies of fuzzers, and fuzzers that are
dependent on given files.
This module assumes that a fuzzer module's imports are done in a normal way. It
will not work on non-toplevel imports.
The following style of imports are supported:
1. from fuzzers.afl import fuzzer
2. from fuzzers.afl import fuzzer as afl_fuzzer

The following are not supported because they will be considered builtin modules.
1. import fuzzers.afl.fuzzer
2. import fuzzers.afl
3. import blah  # Relative-import (against style guide anyway).

This case is not supported because the dependency will not be recognized:
from fuzzers.afl.fuzzer import build

"""
import importlib
import inspect
import types
from typing import Dict, List, Set
import sys

from common import filesystem
from common import fuzzer_utils

# The max depth of dependencies _get_python_dependencies will search.
PY_DEPENDENCIES_MAX_DEPTH = 10

# A cache of Python dependencies for modules. Keys are strings of module paths.
# Values are sets of module paths.
PY_DEPENDENCIES_CACHE: Dict[str, Set[str]] = {}


def _get_fuzzer_module_name(fuzzer: str) -> str:
    """Returns the name of the fuzzer.py module of |fuzzer|. Assumes |fuzzer| is
    an underlying fuzzer."""
    return 'fuzzers.{}.fuzzer'.format(fuzzer)


def is_builtin_module(module: types.ModuleType) -> bool:
    """Returns True if |module| is a python builtin module."""
    return module.__name__ in sys.builtin_module_names


def is_fuzzers_subpath(path: str) -> bool:
    """Returns True if path is a subpath of the fuzzers/ directory."""
    return filesystem.is_subpath(fuzzer_utils.FUZZERS_DIR, path)


def is_fuzzers_submodule(module) -> bool:
    """Returns True if |module| is a submodule of the fuzzers module."""
    if is_builtin_module(module):
        # builtin modules such as "time" don't have files so attempts to get
        # their files fail. Check for these and bail early.
        return False

    # If a module imports `fuzzers` we can't handle it, let the TypeError get
    # thrown so we fail loudly.
    module_path = inspect.getfile(module)
    return is_fuzzers_subpath(module_path)


def get_fuzzer_dependencies(fuzzer: str) -> Set[str]:
    """Returns the list of files in fuzzbench that |fuzzer| depends on. This
    includes dockerfiles used to build |fuzzer|, and the python files it uses to
    build and run fuzz targets."""
    # TODO(metzman): Write a test for this that uses fakefs to enforce that
    # every fuzzer can successfully run with only the dependencies this function
    # finds.
    fuzzer_directory = fuzzer_utils.FuzzerDirectory(fuzzer)

    dependencies = set()

    # Don't use modulefinder for python dependencies since it doesn't work
    # without __init__.py files.
    fuzzer_module = importlib.import_module(_get_fuzzer_module_name(fuzzer))
    dependencies = dependencies.union(_get_python_dependencies(fuzzer_module))

    # The fuzzer is also dependent on dockerfiles.
    dependencies = dependencies.union(fuzzer_directory.dockerfiles)
    return dependencies


def _get_python_dependencies(module: types.ModuleType,
                             depth: int = 0) -> Set[str]:
    """Returns the python files that |module| is dependent on if module is a
    submodule of fuzzers/. Does not return dependencies that are not submodules
    of fuzzers/, such as std library modules. Has a limit of
    PY_DEPENDENCIES_MAX_DEPTH so that cyclic imports can easily be detected.
    Note that this may not work if a fuzzer.py imports modules dynamically or
    within individual functions. That is ok because we can prevent this during
    code review."""
    if depth > PY_DEPENDENCIES_MAX_DEPTH:
        # Enforce a depth to catch cyclic imports.
        format_string = ('Depth: {depth} greater than max: {max_depth}. '
                         'Probably a cyclic import in {module}.')
        raise Exception(
            format_string.format(depth=depth,
                                 max_depth=PY_DEPENDENCIES_MAX_DEPTH,
                                 module=module))

    module_path = inspect.getfile(module)

    # Just get the dependencies from the cache if we have them.
    # This would break on modules doing abnormal things like writing Python
    # files and then importing them, code review should prevent that from
    # landing though.
    if module_path in PY_DEPENDENCIES_CACHE:
        return PY_DEPENDENCIES_CACHE[module_path]

    # Modules depend on themselves.
    dependencies = {module_path}

    # This assumes that every module that |module| depends on is imported in
    # top-level code.
    attr_names = dir(module)
    for attr_name in attr_names:
        # Check if attr_name is a module, bail if not.
        imported_module = getattr(module, attr_name)
        if not isinstance(imported_module, types.ModuleType):
            continue

        # Files in fuzzers/ can only import code from the Python standard
        # library modules and modules in fuzzers/.
        if is_fuzzers_submodule(imported_module):
            imported_module_path = inspect.getfile(imported_module)
            dependencies.add(imported_module_path)
            # Now recur to get the dependencies of the dependency.
            dependencies = dependencies.union(
                _get_python_dependencies(imported_module, depth + 1))

    PY_DEPENDENCIES_CACHE[module_path] = dependencies
    return dependencies


def get_files_dependent_fuzzers(dependency_files: List[str]) -> List[str]:
    """Returns a list of fuzzer names dependent on |dependency_files|."""
    dependency_files = set(dependency_files)
    dependent_fuzzers = []
    for fuzzer in fuzzer_utils.get_fuzzer_names():
        fuzzer_dependencies = get_fuzzer_dependencies(fuzzer)

        if fuzzer_dependencies.intersection(dependency_files):
            dependent_fuzzers.append(fuzzer)

    return dependent_fuzzers
