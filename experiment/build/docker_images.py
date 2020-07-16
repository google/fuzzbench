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

import yaml


def subst(template, fuzzer, benchmark):
    """Replaces {fuzzer} or {benchmark} with |fuzzer| or |benchmark| in
    |template| string."""
    return template.format(fuzzer=fuzzer, benchmark=benchmark)


def instantiate_image_obj(name_template, obj_template, fuzzer, benchmark):
    """Instantiates an image object from a template for a |fuzzer| - |benchmark|
    pair."""
    name = subst(name_template, fuzzer, benchmark)
    obj = obj_template.copy()
    for key in obj:
        if key in ('build_arg', 'depends_on'):
            obj[key] = [subst(item, fuzzer, benchmark) for item in obj[key]]
        else:
            obj[key] = subst(obj[key], fuzzer, benchmark)
    return name, obj


def get_image_type_templates():
    """Loads the image types config that contains "templates" describing how to
    build them and their dependencies."""
    with open('docker/image_types.yaml') as config_file:
        templates = yaml.load(config_file, yaml.SafeLoader)
        return templates


def get_images_to_build(fuzzers, benchmarks):
    """Returns the set of buildable images."""
    images = {}
    templates = get_image_type_templates()
    for fuzzer in fuzzers:
        for benchmark in benchmarks:
            for name_templ, obj_templ in templates.items():
                name, obj = instantiate_image_obj(name_templ, obj_templ, fuzzer,
                                                  benchmark)
                images[name] = obj
    return images
