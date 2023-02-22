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
    sh /rustup.sh --default-toolchain nightly -y && \
    rm /rustup.sh

# Install dependencies.
RUN apt-get update && \
    apt-get remove -y llvm-10 && \
    apt-get install -y \
        build-essential \
        llvm-11 \
        clang-12 \
        cargo && \
    apt-get install -y wget libstdc++5 libtool-bin automake flex bison \
        libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
        apt-utils apt-transport-https ca-certificates joe curl && \
    PATH="/root/.cargo/bin/:$PATH" cargo install cargo-make

# Download libafl.
RUN git clone --branch vhtokens2 \
        https://github.com/AFLplusplus/libafl /libafl && \
        cd /libafl && \
        git checkout 6ffd8f883f00c8e649907c9f5d39167c9dab462e || \
        true

# Compile libafl.
RUN cd /libafl && \
    unset CFLAGS CXXFLAGS && \
    export LIBAFL_EDGES_MAP_SIZE=2621440 && \
    cd ./fuzzers/fuzzbench_tokens && \
    PATH="/root/.cargo/bin/:$PATH" cargo build --release

# Auxiliary weak references.
RUN wget https://gist.githubusercontent.com/andreafioraldi/e5f60d68c98b31665a274207cfd05541/raw/4da351a321f1408df566a9cf2ce7cde6eeab3904/empty_fuzzer_lib.c -O /empty_fuzzer_lib.c && \
    clang -c /empty_fuzzer_lib.c && \
    ar r /emptylib.a *.o
