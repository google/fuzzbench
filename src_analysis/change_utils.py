#!/usr/bin/env python3
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
"""Utilities for finding changed code, particularly fuzzers and benchmarks."""
from common import fuzzer_utils
from common import utils
from typing import List

from src_analysis import benchmark_dependencies
from src_analysis import fuzzer_dependencies


def get_changed_fuzzers(changed_files: List[str] = None) -> List[str]:
    """Returns a list of fuzzers that have changed functionality based
    on the files that have changed in |changed_files| and the files the
    fuzzers depend on."""
    # TODO(metzman): Handle case where docker/... or make changes.
    changed_fuzzers = fuzzer_dependencies.get_files_dependent_fuzzers(
        changed_files)
    return changed_fuzzers


def is_docker_image_dependency(path):
    return os.path.dirname(path) != 'gcb'


def get_docker_image_dependencies():
    return [
        path
        for path in list_files(os.path.join(utils.SRC_ROOT, 'docker'))
        if is_docker_image_dependency(path)
    ]


def get_changed_fuzzers_for_ci(changed_files: List[str] = None) -> List[str]:
    """Returns a list of fuzzers that have changed functionality and should be
    tested based on the files that have changed in |changed_files|, the files
    the fuzzers depend on and files that testing the fuzzers depends on as
    well."""
    # TODO(metzman): Use a more precise method for this when we write docker
    # image dependencies in Python.
    universal_dependencies = [
        os.path.join(utils.SRC_ROOT, 'Makefile')
    ]
    universal_dependencies += get_docker_image_dependencies()
    universal_dependencies += filesystem.list_files(
        os.path.join(utils.SRC_ROOT, '.github'))
    # The module this submodule is a part of.
    universal_dependencies += filesystem.list_files(
            os.path.dirname(__file__))
    if set(changed_files).intersect(universal_dependencies):
        return [
            fuzzer_utils.get_fuzzer_from_config(fuzzer_config)
            for config in fuzzer_utils.get_fuzzer_configs()
        ]
    return get_changed_fuzzers(changed_files)



def get_changed_benchmarks(changed_files: List[str] = None) -> List[str]:
    """Returns a list of benchmarks that have changed functionality based
    on the files that have changed in |changed_files|."""
    changed_benchmarks = benchmark_dependencies.get_files_dependent_benchmarks(
        changed_files)
    return changed_benchmarks
