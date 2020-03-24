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

# Need Clang/LLVM 3.8.
RUN apt-get update -y && \
    apt-get -y install llvm-3.8 \
    clang-3.8 \
    libstdc++-5-dev \
    wget

# Download AFL and compile using default compiler.
# We need afl-2.26b
RUN wget https://lcamtuf.coredump.cx/afl/releases/afl-2.26b.tgz -O /afl-2.26b.tgz && \
    tar xvzf /afl-2.26b.tgz -C / && \
    mv /afl-2.26b /afl && \
    cd /afl && \
    AFL_NO_X86=1 make

# Set the env variables for LLVM passes and test units.
ENV CC=clang-3.8
ENV CXX=clang++-3.8
ENV LLVM_CONFIG=llvm-config-3.8

# Build the LLVM passes with the LAF-INTEL patches, using Clang 3.8.
RUN cd /afl/llvm_mode && \
    wget https://gitlab.com/laf-intel/laf-llvm-pass/raw/master/src/afl.patch && \
    patch -p0 < afl.patch && \
    wget https://gitlab.com/laf-intel/laf-llvm-pass/raw/master/src/compare-transform-pass.so.cc && \
    wget https://gitlab.com/laf-intel/laf-llvm-pass/raw/master/src/split-compares-pass.so.cc && \
    wget https://gitlab.com/laf-intel/laf-llvm-pass/raw/master/src/split-switches-pass.so.cc && \
    CXXFLAGS= CFLAGS= make



RUN ls /usr/local/include/c++/v1/
# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/master/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    $CXX -I/usr/local/include/c++/v1/ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o