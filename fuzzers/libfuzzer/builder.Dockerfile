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

RUN git clone https://github.com/llvm/llvm-project.git /llvm-project && \
    cd /llvm-project/ && \
    git checkout bb54bcf84970c04c9748004f3a4cf59b0c1832a7 && \
    cd compiler-rt/lib/fuzzer && \
    (for f in *.cpp; do \
      clang++ -stdlib=libc++ -fPIC -O2 -std=c++11 $f -c & \
    done && wait) && \
    ar r /usr/lib/libFuzzer.a *.o
