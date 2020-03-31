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
#
# Dockerfile for building a specific benchmark for a specific fuzzer.
#
# The benchmark/fuzzer pair is defined by build arguments. To specify them, pass
# the following arguments to docker build:
#
# $ docker build \
#   --build-arg benchmark=afl \
#   --build-arg fuzzer=freetype2-2017 \
#   ...

# Start from $fuzzer's builder image.
ARG fuzzer
FROM gcr.io/fuzzbench/builders/$fuzzer

# An ARG declared before a FROM is outside of a build stage scope, so we need to
# re-declare it here.
ARG fuzzer
ARG benchmark

# Set up source and output directories.
ENV SRC /src
ENV OUT /out
ENV FUZZ_TARGET $OUT/fuzz-target

WORKDIR $SRC

# Copy the build script to the source directory.
COPY benchmarks/*.sh ./
COPY benchmarks/$benchmark/ ./benchmark

# Copy the fuzzer config script and run build().
COPY fuzzers/$fuzzer/fuzzer.py fuzzer.py

# Copy the entire fuzzers directory tree to allow for module dependencies.
COPY fuzzers fuzzers

# Create empty __init__.py to allow python deps to work.
RUN touch __init__.py

# Create output directory for build artifacts.
RUN mkdir -p $OUT

# Disable LeakSanitizer since ptrace is unavailable in Google Cloud build
# and is not needed during build process.
ENV ASAN_OPTIONS="detect_leaks=0"

RUN python3 -u -c "from fuzzers import utils; utils.initialize_flags(); import fuzzer; fuzzer.build()"
