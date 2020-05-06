# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ARG parent_image
FROM $parent_image

ARG fuzzer
ARG benchmark
ARG checkout_commit
ARG checkout_commit_repo_path

ENV FUZZER $fuzzer
ENV BENCHMARK $benchmark

RUN apt-get update -y && apt-get install -y python3

COPY fuzzers/$fuzzer/fuzzer.py $SRC/fuzzer.py

# Copy the entire fuzzers directory tree to allow for module dependencies.
COPY fuzzers $SRC/fuzzers

# Create empty __init__.py to allow python deps to work.
RUN touch $SRC/__init__.py

# Disable LeakSanitizer since ptrace is unavailable in Google Cloud build
# and is not needed during build process.
ENV ASAN_OPTIONS="detect_leaks=0"

ENV OSS_FUZZ 1

ENV CHECKOUT_COMMIT $checkout_commit
ENV CHECKOUT_COMMIT_REPO_PATH $checkout_commit_repo_path
RUN mkdir /opt/fuzzbench/
COPY docker/oss-fuzz-builder/checkout_commit.py /opt/fuzzbench/
RUN python3 /opt/fuzzbench/checkout_commit.py

RUN PYTHONPATH=$SRC python3 -u -c "from fuzzers import utils; utils.initialize_flags(); import fuzzer; fuzzer.build()"
