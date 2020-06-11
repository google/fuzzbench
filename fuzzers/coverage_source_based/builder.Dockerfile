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

# Use a libFuzzer version that supports source-based coverage
RUN git clone https://github.com/llvm/llvm-project.git /llvm-project && \
    cd /llvm-project && \
    git checkout 2f6bb2a69215f9cae883da12f8f596d3f80f8d71 && \
    cd /llvm-project/compiler-rt/lib/fuzzer && \
    bash build.sh && \
    cp libFuzzer.a /usr/lib