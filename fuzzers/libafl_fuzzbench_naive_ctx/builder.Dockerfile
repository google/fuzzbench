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
    sh /rustup.sh --default-toolchain nightly-2023-03-29 -y && \
    rm /rustup.sh

# Install dependencies.
RUN apt-get update && \
    apt-get remove -y llvm-10 && \
    apt-get install -y \
        build-essential \
        llvm-11 \
        clang-12 && \
    apt-get install -y wget libstdc++5 libtool-bin automake flex bison \
        libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
        apt-utils apt-transport-https ca-certificates joe curl \
        python3-dev gzip && \
    PATH="/root/.cargo/bin/:$PATH" cargo install cargo-make

# Download libafl
RUN git clone https://github.com/AFLplusplus/libafl_fuzzbench /libafl_fuzzbench && \
    cd /libafl_fuzzbench && \
    git checkout 8a5aaf395d8c3160d980334faffdd215f101d1d3 && \
    git submodule update --init

# Compile libafl
RUN cd /libafl_fuzzbench/ && unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export CXX=clang++ && \
    export LIBAFL_EDGES_MAP_SIZE=65536 && \
    PATH="/root/.cargo/bin/:$PATH"  cargo build --release --features no_link_main

# Auxiliary weak references.
RUN cd /libafl_fuzzbench && \
    clang -c stub_rt.c && \
    ar r /stub_rt.a stub_rt.o