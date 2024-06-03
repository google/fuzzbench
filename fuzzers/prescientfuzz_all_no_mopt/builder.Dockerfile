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

# Download PrescientFuzz
RUN git clone https://github.com/DanBlackwell/PrescientFuzz /PrescientFuzz
COPY ./patch /PrescientFuzz/patch
RUN cd /PrescientFuzz && git fetch && git checkout 0299c8eed31c2a06eb064dee3c7cc4d66af90530 && git apply patch

# Compile PrescientFuzz.
RUN cd /PrescientFuzz && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86 && \
    export LIBAFL_EDGES_MAP_SIZE=2621440 && \
    cd ./fuzzers/fuzzbench && \
    PATH="/root/.cargo/bin/:$PATH" cargo +nightly build --profile release-fuzzbench --features no_link_main

# Auxiliary weak references.
RUN cd /PrescientFuzz/fuzzers/fuzzbench && \
    clang -c stub_rt.c && \
    ar r /stub_rt.a stub_rt.o
