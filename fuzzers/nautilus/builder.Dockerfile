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

# Install libstdc++ to use llvm_mode.
RUN apt-get update && \
    apt-get install -y wget libstdc++-10-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates joe curl \
                       python3-dev gzip

# Uninstall old Rust
RUN if which rustup; then rustup self uninstall -y; fi

# Install latest Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /rustup.sh && \
    sh /rustup.sh -y

# Download libafl
RUN git clone https://github.com/AFLplusplus/libafl_fuzzbench /libafl_fuzzbench && \
    cd /libafl_fuzzbench && \
    git checkout b7fc9fd143daff0190fd623ed3a8b9fbc64cc00c && \
    git submodule update --init

# Compile libafl
RUN cd /libafl_fuzzbench/ && unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export CXX=clang++ && \
    export LIBAFL_EDGES_MAP_SIZE=2621440 && \
    PATH="/root/.cargo/bin:$PATH" cargo build --release -p nautilus

RUN wget https://gist.githubusercontent.com/andreafioraldi/e5f60d68c98b31665a274207cfd05541/raw/4da351a321f1408df566a9cf2ce7cde6eeab3904/empty_fuzzer_lib.c -O /empty_fuzzer_lib.c && \
    clang -c /empty_fuzzer_lib.c && \
    ar r /emptylib.a *.o
