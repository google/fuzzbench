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

# Install llvm 12 and gcc 10
RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libexpat1-dev && \
    apt-get install -y apt-utils apt-transport-https ca-certificates && \
    echo deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial main >> /etc/apt/sources.list && \
    echo deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main >> /etc/apt/sources.list && \
    wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add - && \
    apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 1E9377A2BA9EF27F && \
    apt-get update && \
    apt-get install -y clang-12 clangd-12 clang-tools-12 libc++1-12 libc++-12-dev \
      libc++abi1-12 libc++abi-12-dev libclang1-12 libclang-12-dev libclang-common-12-dev \
      libclang-cpp12 libclang-cpp12-dev liblld-12 liblld-12-dev liblldb-12 \
      liblldb-12-dev libllvm12 libomp-12-dev libomp5-12 lld-12 lldb-12 \
      llvm-12 llvm-12-dev llvm-12-runtime llvm-12-tools && \
    apt-get install -y gcc-9 g++-9

# Download afl++
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 2044c7e2b548e2747fde5deff65c78dd05e2ec8d
    
# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && unset CFLAGS && unset CXXFLAGS && \
    export LLVM_CONFIG=llvm-config-12 && export AFL_NO_X86=1 && \
    export REAL_CC=gcc-9 && export REAL_CXX=g++-9 && \
    CC=gcc-9 PYTHON_INCLUDE=/ make && make install && \
    make -C utils/aflpp_driver && \
    cp utils/aflpp_driver/libAFLDriver.a / && \
    cp -va `llvm-config-12 --libdir`/libc++* /afl/
