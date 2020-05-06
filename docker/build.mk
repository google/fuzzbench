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

FUZZERS    := $(notdir $(shell find fuzzers -mindepth 1 -maxdepth 1 -type d))
BENCHMARKS := $(notdir $(shell find benchmarks -type f -name build.sh | xargs dirname))
OSS_FUZZ_BENCHMARKS := $(notdir $(shell find benchmarks -type f -name oss-fuzz.yaml | xargs dirname))

BASE_TAG ?= gcr.io/fuzzbench


build-all: $(addsuffix -all, $(addprefix build-,$(FUZZERS)))
pull-all: $(addsuffix -all, $(addprefix pull-,$(FUZZERS)))

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

base-builder: base-image
	docker build \
    --tag $(BASE_TAG)/base-builder \
    $(call cache_from_base,${BASE_TAG}/base-builder) \
    $(call cache_from_base,gcr.io/oss-fuzz-base/base-clang) \
    docker/base-builder

pull-base-clang:
	docker pull gcr.io/oss-fuzz-base/base-clang

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


define fuzzer_template

.$(1)-builder: base-builder
	docker build \
    --tag $(BASE_TAG)/builders/$(1) \
    --file fuzzers/$(1)/builder.Dockerfile \
    $(call cache_from,${BASE_TAG}/builders/$(1)) \
    fuzzers/$(1)

.pull-$(1)-builder: pull-base-builder
	docker pull $(BASE_TAG)/builders/$(1)

build-$(1)-all: $(addprefix build-$(1)-,$(BENCHMARKS)) $(addprefix build-$(1)-,$(OSS_FUZZ_BENCHMARKS))
pull-$(1)-all: $(addprefix pull-$(1)-,$(BENCHMARKS)) $(addprefix pull-$(1)-,$(OSS_FUZZ_BENCHMARKS))

endef

# Instantiate the above template with all fuzzers.
$(foreach fuzzer,$(FUZZERS),$(eval $(call fuzzer_template,$(fuzzer))))


define fuzzer_benchmark_template
.$(1)-$(2)-builder: .$(1)-builder
	docker build \
    --tag $(BASE_TAG)/builders/$(1)/$(2) \
    --build-arg fuzzer=$(1) \
    --build-arg benchmark=$(2) \
    $(call cache_from,${BASE_TAG}/builders/$(1)/$(2)) \
    --file docker/benchmark-builder/Dockerfile \
    .

.pull-$(1)-$(2)-builder: .pull-$(1)-builder
	docker pull $(BASE_TAG)/builders/$(1)/$(2)

ifneq ($(1), coverage)

.$(1)-$(2)-intermediate-runner: base-runner
	docker build \
    --tag $(BASE_TAG)/runners/$(1)/$(2)-intermediate \
    --file fuzzers/$(1)/runner.Dockerfile \
    $(call cache_from,${BASE_TAG}/runners/$(1)/$(2)-intermediate) \
    fuzzers/$(1)

.pull-$(1)-$(2)-intermediate-runner: pull-base-runner
	docker pull $(BASE_TAG)/runners/$(1)/$(2)-intermediate

.$(1)-$(2)-runner: .$(1)-$(2)-builder .$(1)-$(2)-intermediate-runner
	docker build \
    --tag $(BASE_TAG)/runners/$(1)/$(2) \
    --build-arg fuzzer=$(1) \
    --build-arg benchmark=$(2) \
    $(call cache_from,${BASE_TAG}/runners/$(1)/$(2)) \
    --file docker/benchmark-runner/Dockerfile \
    .

.pull-$(1)-$(2)-runner: .pull-$(1)-$(2)-builder .pull-$(1)-$(2)-intermediate-runner
	docker pull $(BASE_TAG)/runners/$(1)/$(2)

build-$(1)-$(2): .$(1)-$(2)-runner
pull-$(1)-$(2): .pull-$(1)-$(2)-runner

run-$(1)-$(2): .$(1)-$(2)-runner
	docker run \
    --cpus=1 \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$(2) \
    -it \
    $(BASE_TAG)/runners/$(1)/$(2)

test-run-$(1)-$(2): .$(1)-$(2)-runner
	docker run \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$(2) \
    -e MAX_TOTAL_TIME=20 \
    -e SNAPSHOT_PERIOD=10 \
    $(BASE_TAG)/runners/$(1)/$(2)

debug-$(1)-$(2): .$(1)-$(2)-runner
	docker run \
    --cpus=1 \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$(2) \
    --entrypoint "/bin/bash" \
    -it \
    $(BASE_TAG)/runners/$(1)/$(2)

else
# Coverage builds don't need runners.
build-$(1)-$(2): .$(1)-$(2)-builder
pull-$(1)-$(2): .pull-$(1)-$(2)-builder

endif

endef

# Instantiate the above template with the cross product of all fuzzers and
# benchmark.
$(foreach fuzzer,$(FUZZERS), \
  $(foreach benchmark,$(BENCHMARKS), \
    $(eval $(call fuzzer_benchmark_template,$(fuzzer),$(benchmark)))))


define oss_fuzz_benchmark_template
$(1)-project-name := $(shell cat benchmarks/$(1)/oss-fuzz.yaml | \
                             grep project | cut -d ':' -f2 | tr -d ' ')
$(1)-fuzz-target  := $(shell cat benchmarks/$(1)/oss-fuzz.yaml | \
                             grep fuzz_target | cut -d ':' -f2 | tr -d ' ')
$(1)-oss-fuzz-builder-hash := $(shell cat benchmarks/$(1)/oss-fuzz.yaml | \
                                      grep oss_fuzz_builder_hash | \
                                      cut -d ':' -f2 | tr -d ' ')
$(1)-commit  := $(shell cat benchmarks/$(1)/oss-fuzz.yaml | \
                        grep commit | cut -d ':' -f2 | tr -d ' ')
$(1)-repo-path  := $(shell cat benchmarks/$(1)/oss-fuzz.yaml | \
                           grep repo_path| cut -d ':' -f2 | tr -d ' ')
endef
# Instantiate the above template with all OSS-Fuzz benchmarks.
$(foreach oss_fuzz_benchmark,$(OSS_FUZZ_BENCHMARKS), \
  $(eval $(call oss_fuzz_benchmark_template,$(oss_fuzz_benchmark))))


define fuzzer_oss_fuzz_benchmark_template

.$(1)-$(2)-oss-fuzz-builder-intermediate:
	docker build \
    --tag $(BASE_TAG)/builders/$(1)/$(2)-intermediate \
    --file=fuzzers/$(1)/builder.Dockerfile \
    --build-arg parent_image=gcr.io/fuzzbench/oss-fuzz/$($(2)-project-name)@sha256:$($(2)-oss-fuzz-builder-hash) \
    $(call cache_from,${BASE_TAG}/builders/$(1)/$(2)-intermediate) \
    fuzzers/$(1)

.pull-$(1)-$(2)-oss-fuzz-builder-intermediate:
	docker pull $(BASE_TAG)/builders/$(1)/$(2)-intermediate

.$(1)-$(2)-oss-fuzz-builder: .$(1)-$(2)-oss-fuzz-builder-intermediate
	docker build \
    --tag $(BASE_TAG)/builders/$(1)/$(2) \
    --file=docker/oss-fuzz-builder/Dockerfile \
    --build-arg parent_image=$(BASE_TAG)/builders/$(1)/$(2)-intermediate \
    --build-arg fuzzer=$(1) \
    --build-arg benchmark=$(2) \
    --build-arg checkout_commit=$(1)-commit \
    --build-arg checkout_commit_repo_path=$(1)-repo-path \
    $(call cache_from,${BASE_TAG}/builders/$(1)/$(2)) \
    .

.pull-$(1)-$(2)-oss-fuzz-builder: .pull-$(1)-$(2)-oss-fuzz-builder-intermediate
	docker pull $(BASE_TAG)/builders/$(1)/$(2)

ifneq ($(1), coverage)

.$(1)-$(2)-oss-fuzz-intermediate-runner: base-runner
	docker build \
    --tag $(BASE_TAG)/runners/$(1)/$(2)-intermediate \
    --file fuzzers/$(1)/runner.Dockerfile \
    $(call cache_from,${BASE_TAG}/runners/$(1)/$(2)-intermediate) \
    fuzzers/$(1)

.pull-$(1)-$(2)-oss-fuzz-intermediate-runner: pull-base-runner
	docker pull $(BASE_TAG)/runners/$(1)/$(2)-intermediate

.$(1)-$(2)-oss-fuzz-runner: .$(1)-$(2)-oss-fuzz-builder .$(1)-$(2)-oss-fuzz-intermediate-runner
	docker build \
    --tag $(BASE_TAG)/runners/$(1)/$(2) \
    --build-arg fuzzer=$(1) \
    --build-arg benchmark=$(2) \
    $(call cache_from,${BASE_TAG}/runners/$(1)/$(2)) \
    --file docker/oss-fuzz-runner/Dockerfile \
    .

.pull-$(1)-$(2)-oss-fuzz-runner: .pull-$(1)-$(2)-oss-fuzz-builder .pull-$(1)-$(2)-oss-fuzz-intermediate-runner
	docker pull $(BASE_TAG)/runners/$(1)/$(2)

build-$(1)-$(2): .$(1)-$(2)-oss-fuzz-runner

pull-$(1)-$(2): .pull-$(1)-$(2)-oss-fuzz-runner

run-$(1)-$(2): .$(1)-$(2)-oss-fuzz-runner
	docker run \
    --cpus=1 \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$(2) \
    -e FUZZ_TARGET=$($(2)-fuzz-target) \
    -it $(BASE_TAG)/runners/$(1)/$(2)

test-run-$(1)-$(2): .$(1)-$(2)-oss-fuzz-runner
	docker run \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$(2) \
    -e FUZZ_TARGET=$($(2)-fuzz-target) \
    -e MAX_TOTAL_TIME=20 \
    -e SNAPSHOT_PERIOD=10 \
    $(BASE_TAG)/runners/$(1)/$(2)

debug-$(1)-$(2): .$(1)-$(2)-oss-fuzz-runner
	docker run \
    --cpus=1 \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$(2) \
    -e FUZZ_TARGET=$($(2)-fuzz-target) \
    --entrypoint "/bin/bash" \
    -it $(BASE_TAG)/runners/$(1)/$(2)

else

build-$(1)-$(2): .$(1)-$(2)-oss-fuzz-builder
pull-$(1)-$(2): .pull-$(1)-$(2)-oss-fuzz-builder

endif

endef

# Instantiate the above template with the cross product of all fuzzers and
# OSS-Fuzz benchmarks.
$(foreach fuzzer,$(FUZZERS), \
  $(foreach oss_fuzz_benchmark,$(OSS_FUZZ_BENCHMARKS), \
    $(eval $(call fuzzer_oss_fuzz_benchmark_template,$(fuzzer),$(oss_fuzz_benchmark)))))
