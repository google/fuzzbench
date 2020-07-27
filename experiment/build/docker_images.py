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

from common import yaml_utils


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
        if key in ('build_arg', 'depends_on', 'env_vars'):
            obj[key] = [_substitute(it, fuzzer, benchmark) for it in obj[key]]
        else:
            obj[key] = _substitute(obj[key], fuzzer, benchmark)
    return name, obj


def _instantiate_string_gcb(image_types):
    all_templates = {}
    for name in image_types:
        image = image_types[name]
        if 'depends_on' in image.keys():
            image['depends_on'] = [it.lstrip('.') for it in image['depends_on']]
        all_templates[name.lstrip('.')] = image
    return all_templates


def _get_image_type_templates(oss_fuzz, skip_base):
    """Loads the image types config that contains "templates" describing how to
    build them and their dependencies."""
    all_templates = yaml_utils.read('docker/image_types.yaml')
    templates = {}
    for name, image in all_templates.items():
        if 'base' in name or 'dispatcher' in name:
            if not skip_base:
                templates[name] = [image]
            continue
        if oss_fuzz:
            if 'oss-fuzz' in name:
                templates[name] = image
                continue
        elif not oss_fuzz and not 'oss-fuzz' in name:
            templates[name] = image
    return templates


def get_images_to_build_gcb(coverage=False):
    """Returns set of buildable images for GCB."""
    all_templates = _instantiate_string_gcb(
        yaml_utils.read('docker/image_types.yaml'))
    templates = {}
    fuzzer = 'coverage' if coverage else "${_FUZZER}"
    benchmark = "${_BENCHMARK}"
    for name, image in all_templates.items():
        if 'dispatcher' in name:
            continue
        if 'base' in name:
            templates[name] = image
            continue
        sub_name, sub_image = _instantiate_image_obj(name, image, fuzzer,
                                                     benchmark)
        templates[sub_name] = sub_image
    return templates


def get_images_to_build(fuzzers, benchmarks, oss_fuzz=False, skip_base=False):
    """Returns the set of buildable images."""
    images = {}
    templates = _get_image_type_templates(oss_fuzz, skip_base)
    for fuzzer in fuzzers:
        for benchmark in benchmarks:
            for name_templ, obj_templ in templates.items():
                if fuzzer in ('coverage', 'coverage_source_based'):
                    if 'runner' in name_templ:
                        continue
                if 'base' in name_templ or 'dispatcher' in name_templ:
                    images[name_templ] = obj_templ[0]
                    continue
                name, obj = _instantiate_image_obj(name_templ, obj_templ,
                                                   fuzzer, benchmark)
                images[name] = obj
    return images
