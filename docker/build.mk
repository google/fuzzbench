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

FUZZERS    := $(notdir $(shell find fuzzers -mindepth 1 -maxdepth 1 -type d | grep -v coverage))
BENCHMARKS := $(notdir $(shell find benchmarks -type f -name build.sh | xargs dirname))
OSS_FUZZ_PROJECTS := $(notdir $(shell find benchmarks -type f -name oss-fuzz.yaml | xargs dirname))

BASE_TAG := gcr.io/fuzzbench


build-all: $(addsuffix -all, $(addprefix build-,$(FUZZERS)))


base-image:
	docker build \
    --tag $(BASE_TAG)/base-image \
    docker/base-image

base-builder: base-image
	docker build \
    --tag $(BASE_TAG)/base-builder \
    docker/base-builder

base-runner: base-image
	docker build \
    --tag $(BASE_TAG)/base-runner \
    docker/base-runner

dispatcher-image: base-image
	docker build \
    --tag $(BASE_TAG)/dispatcher-image \
    docker/dispatcher-image


define fuzzer_template

.$(1)-builder: base-builder
	docker build \
    --tag $(BASE_TAG)/builders/$(1) \
    --file fuzzers/$(1)/builder.Dockerfile \
    fuzzers/$(1)

build-$(1)-all: $(addprefix build-$(1)-,$(BENCHMARKS))

endef

# Instantiate the above template with all fuzzers.
$(foreach fuzzer,$(FUZZERS),$(eval $(call fuzzer_template,$(fuzzer))))


define fuzzer_benchmark_template
.$(1)-$(2)-builder: .$(1)-builder
	docker build \
    --tag $(BASE_TAG)/builders/$(1)/$(2) \
    --build-arg fuzzer=$(1) \
    --build-arg benchmark=$(2) \
    --file docker/benchmark-builder/Dockerfile \
    .

.$(1)-$(2)-intermediate-runner: base-runner
	docker build \
    --tag $(BASE_TAG)/runners/$(1)/$(2)-intermediate \
    --file fuzzers/$(1)/runner.Dockerfile \
    fuzzers/$(1)

.$(1)-$(2)-runner: .$(1)-$(2)-builder .$(1)-$(2)-intermediate-runner
	docker build \
    --tag $(BASE_TAG)/runners/$(1)/$(2) \
    --build-arg fuzzer=$(1) \
    --build-arg benchmark=$(2) \
    --file docker/benchmark-runner/Dockerfile \
    .

build-$(1)-$(2): .$(1)-$(2)-runner

run-$(1)-$(2): .$(1)-$(2)-runner
	docker run \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$(2) \
    -it \
    $(BASE_TAG)/runners/$(1)/$(2)

debug-$(1)-$(2): .$(1)-$(2)-runner
	docker run \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$(2) \
    --entrypoint "/bin/bash" \
    -it \
    $(BASE_TAG)/runners/$(1)/$(2)

endef

# Instantiate the above template with the cross product of all fuzzers and
# benchmark.
$(foreach fuzzer,$(FUZZERS), \
  $(foreach benchmark,$(BENCHMARKS), \
    $(eval $(call fuzzer_benchmark_template,$(fuzzer),$(benchmark)))))


define oss_fuzz_project_template
$(1)-project-name := $(shell cat benchmarks/$(1)/oss-fuzz.yaml | \
                             grep project | cut -d ':' -f2 | tr -d ' ')
$(1)-fuzz-target  := $(shell cat benchmarks/$(1)/oss-fuzz.yaml | \
                             grep fuzz_target | cut -d ':' -f2 | tr -d ' ')
$(1)-oss-fuzz-builder-hash := $(shell cat benchmarks/$(1)/oss-fuzz.yaml | \
                                      grep oss_fuzz_builder_hash | \
                                      cut -d ':' -f2 | tr -d ' ')
endef
# Instantiate the above template with all OSS-Fuzz projects.
$(foreach oss_fuzz_project,$(OSS_FUZZ_PROJECTS), \
  $(eval $(call oss_fuzz_project_template,$(oss_fuzz_project))))


define fuzzer_oss_fuzz_project_template

.$(1)-$(2)-oss-fuzz-builder-intermediate:
	docker build \
    --tag $(BASE_TAG)/oss-fuzz/builders/$(1)/$($(2)-project-name)-intermediate \
    --file=fuzzers/$(1)/builder.Dockerfile \
    --build-arg parent_image=gcr.io/fuzzbench/oss-fuzz/$($(2)-project-name)@sha256:$($(2)-oss-fuzz-builder-hash) \
    fuzzers/$(1)

.$(1)-$(2)-oss-fuzz-builder: .$(1)-$(2)-oss-fuzz-builder-intermediate
	docker build \
    --tag $(BASE_TAG)/oss-fuzz/builders/$(1)/$($(2)-project-name) \
    --file=docker/oss-fuzz-builder/Dockerfile \
    --build-arg parent_image=$(BASE_TAG)/oss-fuzz/builders/$(1)/$($(2)-project-name)-intermediate \
    --build-arg fuzzer=$(1) \
    .

.$(1)-$(2)-oss-fuzz-intermediate-runner: base-runner
	docker build \
    --tag $(BASE_TAG)/oss-fuzz/runners/$(1)/$($(2)-project-name)-intermediate \
    --file fuzzers/$(1)/runner.Dockerfile \
    fuzzers/$(1)

.$(1)-$(2)-oss-fuzz-runner: .$(1)-$(2)-oss-fuzz-builder .$(1)-$(2)-oss-fuzz-intermediate-runner
	docker build \
    --tag $(BASE_TAG)/oss-fuzz/runners/$(1)/$($(2)-project-name) \
    --build-arg fuzzer=$(1) \
    --build-arg oss_fuzz_project=$($(2)-project-name) \
    --file docker/oss-fuzz-runner/Dockerfile \
    .

build-$(1)-$(2): .$(1)-$(2)-oss-fuzz-runner

run-$(1)-$(2): .$(1)-$(2)-oss-fuzz-runner
	docker run \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$($(2)-project-name) \
    -e FUZZ_TARGET=$($(2)-fuzz-target) \
    -it $(BASE_TAG)/oss-fuzz/runners/$(1)/$($(2)-project-name)

debug-$(1)-$(2): .$(1)-$(2)-oss-fuzz-runner
	docker run \
    --cap-add SYS_NICE \
    --cap-add SYS_PTRACE \
    -e FUZZ_OUTSIDE_EXPERIMENT=1 \
    -e TRIAL_ID=1 \
    -e FUZZER=$(1) \
    -e BENCHMARK=$($(2)-project-name) \
    -e FUZZ_TARGET=$($(2)-fuzz-target) \
    --entrypoint "/bin/bash" \
    -it $(BASE_TAG)/oss-fuzz/runners/$(1)/$($(2)-project-name)

endef

# Instantiate the above template with the cross product of all fuzzers and
# OSS-Fuzz projects.
$(foreach fuzzer,$(FUZZERS), \
  $(foreach oss_fuzz_project,$(OSS_FUZZ_PROJECTS), \
    $(eval $(call fuzzer_oss_fuzz_project_template,$(fuzzer),$(oss_fuzz_project)))))
