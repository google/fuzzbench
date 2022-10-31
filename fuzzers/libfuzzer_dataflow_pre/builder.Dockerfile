# Copyright 2022 Google LLC
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

ADD https://commondatastorage.googleapis.com/chromium-browser-clang/Linux_x64/clang-llvmorg-15-init-1995-g5bec1ea7-1.tgz /
RUN mkdir /clang && \
    tar zxvf /clang-llvmorg-15-init-1995-g5bec1ea7-1.tgz -C /clang

RUN git clone \
    --depth 1 \
    --branch llvmorg-15.0.3 \
    https://github.com/llvm/llvm-project.git /llvm-project && \
    cd /llvm-project/compiler-rt/lib/fuzzer && \
    (for f in *.cpp; do \
      clang++ -stdlib=libc++ -fPIC -O2 -std=c++14 $f -c & \
    done && wait) && \
    ar r /usr/lib/libFuzzer.a *.o
