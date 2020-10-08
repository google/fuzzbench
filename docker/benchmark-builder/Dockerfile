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

# Using multi-stage build to copy latest Python 3.
FROM gcr.io/fuzzbench/base-image AS base-image

FROM $parent_image

ARG fuzzer
ARG benchmark

ENV FUZZER $fuzzer
ENV BENCHMARK $benchmark

# Copy latest python3 from base-image into local.
COPY --from=base-image /usr/local/bin/python3* /usr/local/bin/
COPY --from=base-image /usr/local/lib/python3.7 /usr/local/lib/python3.7
COPY --from=base-image /usr/local/include/python3.7m /usr/local/include/python3.7m

COPY fuzzers/$fuzzer/fuzzer.py $SRC/fuzzer.py

# Copy the entire fuzzers directory tree to allow for module dependencies.
COPY fuzzers $SRC/fuzzers

# Create empty __init__.py to allow python deps to work.
RUN touch $SRC/__init__.py

# Disable LeakSanitizer since ptrace is unavailable in Google Cloud build
# and is not needed during build process.
ENV ASAN_OPTIONS="detect_leaks=0"

RUN mkdir /opt/fuzzbench/
COPY docker/benchmark-builder/checkout_commit.py /opt/fuzzbench/
COPY benchmarks/$benchmark/benchmark.yaml /
RUN export CHECKOUT_COMMIT=$(cat /benchmark.yaml | tr -d ' ' | grep 'commit:' | cut -d ':' -f2) && \
    python3 -u /opt/fuzzbench/checkout_commit.py $CHECKOUT_COMMIT $SRC

RUN export FUZZ_TARGET=$(cat /benchmark.yaml | tr -d ' ' | grep 'fuzz_target:' | cut -d ':' -f2) && \
    PYTHONPATH=$SRC python3 -u -c "from fuzzers import utils; utils.initialize_flags(); import fuzzer; fuzzer.build()"
