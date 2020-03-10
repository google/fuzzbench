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

ARG parent_image=gcr.io/fuzzbench/base-builder
FROM $parent_image

# honggfuzz requires libfd and libunwid.
RUN apt-get update -y && apt-get install -y libbfd-dev libunwind-dev libblocksruntime-dev

# Download honggfuz version 2.1 + 815ccf8e9580b8c83ee673211da9fa217d354b5f
# Set CFLAGS use honggfuzz's defaults except for -mnative which can build CPU
# dependent code that may not work on the machines we actually fuzz on.
# Create an empty object file which will become the FUZZER_LIB lib (since
# honggfuzz doesn't need this when hfuzz-clang(++) is used).
RUN git clone https://github.com/google/honggfuzz.git /honggfuzz && \
    cd /honggfuzz && \
    git checkout 815ccf8e9580b8c83ee673211da9fa217d354b5f && \
    CFLAGS="-O3 -funroll-loops" make && \
    touch empty_lib.c && \
    cc -c -o empty_lib.o empty_lib.c
