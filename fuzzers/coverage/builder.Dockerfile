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

# The patch adds hook to dump clang coverage data when timeout.
COPY patch.diff /

# Use a libFuzzer version that supports clang source-based coverage.
RUN git clone https://github.com/llvm/llvm-project.git /llvm-project && \
    cd /llvm-project && \
    git checkout 0b5e6b11c358e704384520dc036eddb5da1c68bf && \
    patch -p1 < /patch.diff && \
    cd /llvm-project/compiler-rt/lib/fuzzer && \
    bash build.sh && \
    cp libFuzzer.a /usr/lib
