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
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && git checkout dev && \
    git checkout ef2ccc8117bb899616472e2d95525ae0ca1a2098 && \
    AFL_NO_X86=1 make PYTHON_INCLUDE=/ && \
    cd llvm_mode && CXXFLAGS= make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar ru /libAFLDriver.a *.o
