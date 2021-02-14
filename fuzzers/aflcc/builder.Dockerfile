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
    wget \
    make \
    gcc \
    cmake \
    texinfo \
    bison \
    software-properties-common

# Install some libraries needed by some oss-fuzz benchmarks
RUN apt-get install -y zlib1g-dev \
    libarchive-dev \
    libglib2.0-dev \
    libpsl-dev \
    libbsd-dev

# Set env variables.
ENV AFL_CONVERT_COMPARISON_TYPE=NONE
ENV AFL_COVERAGE_TYPE=ORIGINAL
ENV AFL_BUILD_TYPE=FUZZING
ENV AFL_DICT_TYPE=NORMAL
ENV LLVM_CONFIG=llvm-config-3.8


# Download and compile aflcc.
# Note: the commit number is for branch 'nodebug'
RUN git clone https://github.com/Samsung/afl_cc.git /afl && \
    cd /afl && \
    git checkout c9486dfdf35b7d5f58ce4f9dae141031d2f9f3f1 && \
    AFL_NO_X86=1 make && \
    cd /afl/llvm_mode && \
    CC=clang-3.8 CXX=clang++-3.8 CFLAGS= CXXFLAGS= make

# Install gllvm
RUN cd /afl && \
    sh ./setup-aflc-gclang.sh

# Use afl_driver.cpp from LLVM as our fuzzing library.
ENV CC=/afl/aflc-gclang
ENV CXX=/afl/aflc-gclang++
COPY aflcc_mock.c /aflcc_mock.c
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    sed -i -e '/decide_deferred_forkserver/,+8d' /afl/afl_driver.cpp && \
    $CXX -I/usr/local/include/c++/v1/ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp -o /afl/afl_driver.o && \
    ar r /libAFL.a /afl/afl_driver.o && \
    clang-3.8 -O2 -c -fPIC /aflcc_mock.c -o /aflcc_mock.o && \
    clang-3.8 -shared -o /libAflccMock.so /aflcc_mock.o
    
