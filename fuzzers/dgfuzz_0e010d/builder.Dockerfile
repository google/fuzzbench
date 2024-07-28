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

# Uninstall old Rust & Install the latest one.
RUN if which rustup; then rustup self uninstall -y; fi && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /rustup.sh && \
    sh /rustup.sh -y && \
    /root/.cargo/bin/rustup toolchain install nightly && \
    rm /rustup.sh

RUN apt-get update && \
    apt-get install -y \
        build-essential \
        cargo && \
    apt-get install -y wget libstdc++5 libtool-bin automake flex bison \
        libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
        apt-utils apt-transport-https ca-certificates joe curl && \
    PATH="/root/.cargo/bin/:$PATH" cargo install cargo-make


# Download DGFuzz.
RUN git clone https://github.com/DanBlackwell/DGFuzz /dgfuzz

# Checkout a current commit
RUN cd /dgfuzz && git pull && git checkout 0e010d256ec3f191545b21cbecf6cb50886134ff || true

# apply a patch (local testing only)
# COPY ./patch /dgfuzz/patch
# RUN cd /dgfuzz && git apply ./patch

# Compile DGFuzz.
RUN cd /dgfuzz && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86 && \
    cd ./fuzzers/fuzzbench_dataflow_guided && \
    PATH="/root/.cargo/bin/:$PATH" cargo +nightly build --profile release-fuzzbench --features no_link_main

# Auxiliary weak references.
RUN cd /dgfuzz/fuzzers/fuzzbench_dataflow_guided && \
    clang -c stub_rt.c && \
    ar r /stub_rt.a stub_rt.o

# install AFL++ dependencies
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

# compile afl-clang-dgfuzz
RUN cd /dgfuzz/fuzzers/fuzzbench_dataflow_guided/afl-cc && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    cd utils/aflpp_driver/ && \
    PYTHON_INCLUDE=/ make && \
    cp ./libAFLDriver.a /
    

