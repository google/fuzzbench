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

# Install wget to download afl_driver.cpp. Install libstdc++ to use llvm_mode.
RUN apt-get update && \
    apt-get install wget libstdc++-5-dev -y

# Download and compile afl++ (v2.62d).
# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.

RUN rm -rf /afl && git clone https://github.com/alifahmed/aflmod /afl && \
    cd /afl && \
    git checkout 439f6461183c44c7509a8888b5515ab0a63311bc && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN cd /afl && clang++ -stdlib=libc++ -std=c++11 -O3 -c cgs_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -O3 -I/afl && \
    ar r /libAFL.a *.o
