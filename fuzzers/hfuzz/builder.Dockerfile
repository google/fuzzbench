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

RUN apt-get update && \
    apt-get install -y \
        build-essential \
        python3-dev \
        python3-setuptools \
        automake \
        cmake \
        git \
        flex \
        bison \
        libglib2.0-dev \
        libpixman-1-dev \
        cargo \
        libgtk-3-dev \
        # for QEMU mode
        ninja-build \
        gcc-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-plugin-dev \
        libstdc++-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-dev

RUN git clone https://github.com/Yu3H0/HFuzz.git /hfuzz1
RUN git -C /hfuzz1 checkout hfuzz1

RUN git clone https://github.com/Yu3H0/HFuzz.git /hfuzz2
RUN git -C /hfuzz2 checkout hfuzz2

RUN git clone https://github.com/Yu3H0/HFuzz.git /hfuzz3
RUN git -C /hfuzz3 checkout hfuzz3

# Download afl++.
RUN git clone -b dev https://github.com/AFLplusplus/AFLplusplus /afl_vanilla  && \
    cd /afl_vanilla  && \
    git checkout tags/v4.30c || \
    true

# Install dependencies.
RUN apt-get update && \
    apt-get remove -y llvm-10 && \
    apt-get install -y \
        build-essential \
        lsb-release wget software-properties-common gnupg && \
    apt-get install -y wget libstdc++5 libtool-bin automake flex bison \
        libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
        apt-utils apt-transport-https ca-certificates libc6-dev joe curl

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl_vanilla && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang-15 AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    cp utils/aflpp_driver/libAFLDriver.a /

RUN cd /hfuzz1 && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang-15 AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    cp utils/aflpp_driver/libAFLDriver.a /

RUN cd /hfuzz2 && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang-15 AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    cp utils/aflpp_driver/libAFLDriver.a /

# The hfuzz3 fuzzer
COPY ./ensemble_runner.py /hfuzz2/ensemble_runner.py
# COPY ./hfuzz3 /hfuzz3
RUN cd /hfuzz3 && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang-15 AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ CFLAGS="-DAFL_CFG_PATH=\\\"/out/hfuzz3/hfuzz3_sancov_cfg\\\"" CXXFLAGS="-DAFL_CFG_PATH=\\\"/out/hfuzz3/hfuzz3_sancov_cfg\\\"" make source-only && \
    cp utils/aflpp_driver/libAFLDriver.a /


RUN if which rustup; then rustup self uninstall -y; fi && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /rustup.sh && \
    sh /rustup.sh --default-toolchain nightly-2024-08-12 -y && \
    rm /rustup.sh


RUN wget https://gist.githubusercontent.com/tokatoka/26f4ba95991c6e33139999976332aa8e/raw/698ac2087d58ce5c7a6ad59adce58dbfdc32bd46/createAliases.sh && \
    chmod u+x ./createAliases.sh && ./createAliases.sh 
# RUN rustup component add rustfmt clippy

# Download libafl.
RUN git clone https://github.com/AFLplusplus/LibAFL /libafl

# Checkout a current commit
RUN cd /libafl && git pull && git checkout f856092f3d393056b010fcae3b086769377cba18 || true
# Note that due a nightly bug it is currently fixed to a known version on top!

# Compile libafl.
RUN cd /libafl && \
    unset CFLAGS CXXFLAGS && \
    export LIBAFL_EDGES_MAP_SIZE=2621440 && \
    cd ./fuzzers/fuzzbench/fuzzbench && \
    PATH="/root/.cargo/bin/:$PATH" cargo build --profile release-fuzzbench --features no_link_main

# Auxiliary weak references.
RUN cd /libafl/fuzzers/fuzzbench/fuzzbench && \
    clang -c stub_rt.c && \
    ar r /stub_rt.a stub_rt.o


# RUN cargo install cargo-make
# build afl-cc, afl-cxx compilers

# RUN cd $SRC && ls ./build.sh
# RUN cd $SRC && CC=/libafl/fuzzers/fuzzbench/fuzzbench/target/release-fuzzbench/libafl_cc \
#     CXX=/libafl/fuzzers/fuzzbench/fuzzbench/target/release-fuzzbench/libafl_cxx \
#     CFLAGS= CXXFLAGS= FUZZER_LIB="/stub_rt.a /libafl/fuzzers/fuzzbench/fuzzbench/target/release-fuzzbench/libfuzzbench.a" \
#     ./build.sh 
# RUN mv $OUT/cms_transform_fuzzer $OUT/libafl_target_bin
# RUN $OUT/libafl_target_bin --help 

