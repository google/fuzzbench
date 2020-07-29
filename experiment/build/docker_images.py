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
"""Provides the set of buildable images and their dependencies."""

import os
from common import yaml_utils

BENCHMARK_DIR = os.path.join(os.path.dirname(__file__),
                             os.pardir, os.pardir, 'benchmarks')
FUZZERS_DIR = os.path.join(os.path.dirname(__file__),
                           os.pardir, os.pardir, 'fuzzers')

def _substitute(template, fuzzer, benchmark):
    """Replaces {fuzzer} or {benchmark} with |fuzzer| or |benchmark| in
    |template| string."""
    return template.format(fuzzer=fuzzer, benchmark=benchmark)


def _instantiate_image_obj(name_template, obj_template, fuzzer, benchmark):
    """Instantiates an image object from a template for a |fuzzer| - |benchmark|
    pair."""
    name = _substitute(name_template, fuzzer, benchmark)
    obj = obj_template.copy()
    for key in obj:
        if key in ('build_arg', 'depends_on'):
            obj[key] = [_substitute(it, fuzzer, benchmark) for it in obj[key]]
        else:
            obj[key] = _substitute(obj[key], fuzzer, benchmark)
    return name, obj


def _get_image_type_templates():
    """Loads the image types config that contains "templates" describing how to
    build them and their dependencies."""
    all_templates = yaml_utils.read('docker/image_types.yaml')
    return all_templates


def get_fuzzers_and_benchmarks():
    """Returns list of fuzzers, and benchmarks."""
    fuzzers = []
    benchmarks = []

    for benchmark in os.listdir(BENCHMARK_DIR):
        benchmark_path = os.path.join(BENCHMARK_DIR, benchmark)
        if not os.path.isdir(benchmark_path):
            continue
        if os.path.exists(os.path.join(benchmark_path, 'benchmark.yaml')):
            benchmarks.append(benchmark)

    for fuzzer in os.listdir(FUZZERS_DIR):
        fuzzer_dir = os.path.join(FUZZERS_DIR, fuzzer)
        if not os.path.isdir(fuzzer_dir):
            continue
        fuzzers.append(fuzzer)

    return fuzzers, benchmarks


def get_images_to_build(fuzzers, benchmarks):
    """Returns the set of buildable images."""
    images = {}
    templates = _get_image_type_templates()
    for fuzzer in fuzzers:
        for benchmark in benchmarks:
            for name_templ, obj_templ in templates.items():
                if fuzzer in ('coverage', 'coverage_source_based'):
                    if 'runner' in name_templ:
                        continue
                if 'base' in name_templ or 'dispatcher' in name_templ:
                    images[name_templ] = obj_templ
                    continue
                name, obj = _instantiate_image_obj(name_templ, obj_templ,
                                                   fuzzer, benchmark)
                images[name] = obj
    return images
