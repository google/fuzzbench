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
    apt-get remove -y llvm-10 && \
    apt-get install -y \
        build-essential \
        llvm-11 \
        clang-12 && \
    apt-get install -y wget libstdc++5 libtool-bin automake flex bison \
        libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
        apt-utils apt-transport-https ca-certificates joe curl

# Uninstall old Rust & Install the latest one.
RUN if which rustup; then rustup self uninstall -y; fi && \
    curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /rustup.sh && \
    sh /rustup.sh --default-toolchain nightly-2023-08-23 -y && \
    rm /rustup.sh

# Download libafl.
RUN git clone https://github.com/AFLplusplus/libafl /libafl && \
    cd /libafl && \
    git checkout defe9084aed5a80ac32fe9a1f3ff00baf97738c6 && \
    unset CFLAGS CXXFLAGS && \
    export LIBAFL_EDGES_MAP_SIZE=2621440 && \
    cd ./libafl_libfuzzer/libafl_libfuzzer_runtime && \
    env -i CXX=$CXX CC=$CC PATH="/root/.cargo/bin/:$PATH" cargo build --profile release-fuzzbench && \
    cp ./target/release-fuzzbench/libafl_libfuzzer_runtime.a /usr/lib/libFuzzer.a
