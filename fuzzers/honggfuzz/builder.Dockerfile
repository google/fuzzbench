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

# Download honggfuz version 2.1 + 77ea4dc4b499799e20ba33ef5df0152ecd113925
# Set CFLAGS use honggfuzz's defaults except for -mnative which can build CPU
# dependent code that may not work on the machines we actually fuzz on.
RUN git clone https://github.com/google/honggfuzz.git /honggfuzz && \
    cd /honggfuzz && \
    git checkout 77ea4dc4b499799e20ba33ef5df0152ecd113925 && \
    CFLAGS="-O3 -funroll-loops" make
