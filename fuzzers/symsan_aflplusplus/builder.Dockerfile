# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# # http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

ARG parent_image
FROM $parent_image

RUN apt-get update &&  \
    apt-get install -y \
    # from afl++
    build-essential \
    python3-dev \
    python3-setuptools \
    autoconf \
    automake \
    cmake \
    ninja-build \
    git \
    flex \
    bison \
    libglib2.0-dev \
    libpixman-1-dev \
    libgtk-3-dev \
    libnl-genl-3-dev \
    # for llvm script
    lsb-release \
    wget \
    software-properties-common \
    gnupg

# add llvm repository
RUN wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 12

# install symsan dependencies
RUN apt install -y \
    llvm-12 \
    clang-12 \
    libc++-12-dev \
    libc++abi-12-dev \
    libunwind-12 \
    python-is-python3 \
    zlib1g-dev \
    libz3-dev \
    libgoogle-perftools-dev


# Download afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 407c || \
    true

# Build afl++
run cd /afl && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang-12 LLVM_CONFIG=llvm-config-12 AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make NO_PYTHON=1 NO_NYX=1 source-only -j && make install && \
    cp utils/aflpp_driver/libAFLDriver.a /

# Download symsan
RUN git clone https://github.com/R-Fuzz/symsan /symsan && \
    cd /symsan && \
    git checkout aflpp

# Build symsan
RUN cd /symsan && \
    mkdir build && \
    cd build && \
    unset CFLAGS CXXFLAGS && \
    CC=clang-12 CXX=clang++-12 CXXFLAGS="-DDEBUG=0" cmake -DAFLPP_PATH=/afl ../ && \
    make -j && make install

COPY libfuzz-harness-proxy.c /
RUN KO_DONT_OPTIMIZE=1 KO_CC=clang-12 KO_USE_FASTGEN=1 /usr/local/bin/ko-clang -c /libfuzz-harness-proxy.c -o /libfuzzer-harness.o
