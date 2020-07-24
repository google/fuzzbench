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
BENCHMARKS := $(notdir $(shell find benchmarks -type f -name benchmark.yaml | xargs dirname))

BASE_TAG ?= gcr.io/fuzzbench

# If we're running on a CI service, cache-from a remote image. Otherwise just
# use the local cache.
cache_from = $(if ${RUNNING_ON_CI},--cache-from $(1),)

# For base-* images (and those that depend on it), use a remote cache by
# default, unless the developer sets DISABLE_REMOTE_CACHE_FOR_BASE.
cache_from_base = $(if ${DISABLE_REMOTE_CACHE_FOR_BASE},,--cache-from $(1))

base-image:
	docker build \
    --tag $(BASE_TAG)/base-image \
    $(call cache_from_base,${BASE_TAG}/base-image) \
    docker/base-image

pull-base-image:
	docker pull $(BASE_TAG)/base-image

pull-base-clang:
	docker pull gcr.io/oss-fuzz-base/base-clang

base-builder: base-image pull-base-clang
	docker build \
    --tag $(BASE_TAG)/base-builder \
    $(call cache_from_base,${BASE_TAG}/base-builder) \
    $(call cache_from_base,gcr.io/oss-fuzz-base/base-clang) \
    docker/base-builder

pull-base-builder: pull-base-image pull-base-clang
	docker pull $(BASE_TAG)/base-builder

base-runner: base-image
	docker build \
    --tag $(BASE_TAG)/base-runner \
    $(call cache_from_base,${BASE_TAG}/base-runner) \
    docker/base-runner

pull-base-runner: pull-base-image
	docker pull $(BASE_TAG)/base-runner

dispatcher-image: base-image
	docker build \
    --tag $(BASE_TAG)/dispatcher-image \
    $(call cache_from,${BASE_TAG}/dispatcher-image) \
    docker/dispatcher-image

define oss_fuzz_benchmark_template
$(1)-fuzz-target  := $(shell cat benchmarks/$(1)/benchmark.yaml | \
                             grep fuzz_target | cut -d ':' -f2 | tr -d ' ')
$(1)-commit := $(shell cat benchmarks/$(1)/benchmark.yaml | \
                           grep commit: | cut -d ':' -f2 | tr -d ' ')

.$(1)-project-builder:
	docker build \
    --tag $(BASE_TAG)/builders/oss-fuzz-project/$(1) \
    --file benchmarks/$(1)/Dockerfile \
    $(call cache_from,${BASE_TAG}/builders/oss-fuzz-project/$(1)) \
    benchmarks/$(1)

endef
# Instantiate the above template with all OSS-Fuzz benchmarks.
$(foreach oss_fuzz_benchmark,$(OSS_FUZZ_BENCHMARKS), \
  $(eval $(call oss_fuzz_benchmark_template,$(oss_fuzz_benchmark))))
