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
ARG debug_builder

ENV FUZZER $fuzzer
ENV BENCHMARK $benchmark
ENV DEBUG_BUILDER $debug_builder

# Copy latest python3 from base-image into local.
COPY --from=base-image /usr/local/bin/python3* /usr/local/bin/
COPY --from=base-image /usr/local/lib/python3.8 /usr/local/lib/python3.8
COPY --from=base-image /usr/local/include/python3.8 /usr/local/include/python3.8
COPY --from=base-image /usr/local/lib/python3.8/site-packages /usr/local/lib/python3.8/site-packages

# Copy the entire fuzzers directory tree to allow for module dependencies.
COPY fuzzers $SRC/fuzzers

# Create empty __init__.py to allow python deps to work.
RUN touch $SRC/__init__.py

# Disable LeakSanitizer since ptrace is unavailable in Google Cloud build
# and is not needed during build process.
ENV ASAN_OPTIONS="detect_leaks=0"

COPY benchmarks/$benchmark/benchmark.yaml /

RUN mkdir /opt/fuzzbench/
COPY docker/benchmark-builder/checkout_commit.py /opt/fuzzbench/
RUN export CHECKOUT_COMMIT=$(cat /benchmark.yaml | tr -d ' ' | grep 'commit:' | cut -d ':' -f2) && \
    python3 -u /opt/fuzzbench/checkout_commit.py $CHECKOUT_COMMIT $SRC
RUN echo "#!/bin/bash\nPYTHONPATH=$SRC python3 -u -c \"from fuzzers import utils; utils.initialize_env(); from fuzzers.$FUZZER import fuzzer; fuzzer.build()\"" > /usr/bin/fuzzer_build && \
    chmod +x /usr/bin/fuzzer_build
RUN echo "Run fuzzer_build to build the target" && if [ -z "$debug_builder" ] ; then fuzzer_build; fi
