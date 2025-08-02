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
    sh /rustup.sh --default-toolchain nightly-2023-09-21 -y && \
    rm /rustup.sh

# Install dependencies.
RUN apt-get update && \
    apt-get remove -y llvm-10 && \
    apt-get install -y \
        build-essential \
        lsb-release wget software-properties-common gnupg && \
    apt-get install -y wget libstdc++5 libtool-bin automake flex bison \
        libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
        apt-utils apt-transport-https ca-certificates joe curl && \
    wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 13

# Copy Bulbasaur
COPY bulbasaur.zip /bulbasaur.zip
 
RUN apt-get update && apt-get install -y unzip && \
    unzip /bulbasaur.zip -d /

# Complie Bulbasaur Fuzzer
RUN cd /bulbasaur && PATH="/root/.cargo/bin/:$PATH" cargo build --release

RUN cd /bulbasaur/afl_llvm_mode && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang-13 CXX=clang++-13 AFL_NO_X86=1 && \
    make && \
    make -C ./aflpp_driver && \
    cp ./libAFLDriver.a /