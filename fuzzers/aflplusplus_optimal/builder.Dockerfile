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

# Install wget to download afl_driver.cpp. Install libstdc++ to use llvm_mode.
#    sed -i 's/https:/http:/g' /etc/apt/sources.list /etc/apt/sources.list.d/* && \
RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libexpat1-dev && \
    apt-get install -y apt-utils apt-transport-https ca-certificates && \
    echo deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-11 main >> /etc/apt/sources.list && \
    echo deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main >> /etc/apt/sources.list && \
    wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add - && \
    apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 1E9377A2BA9EF27F && \
    apt-get update && \
    apt-get install -y clang-11 clangd-11 clang-tools-11 libc++1-11 libc++-11-dev \
      libc++abi1-11 libc++abi-11-dev libclang1-11 libclang-11-dev libclang-common-11-dev \
      libclang-cpp11 libclang-cpp11-dev liblld-11 liblld-11-dev liblldb-11 \
      liblldb-11-dev libllvm11 libomp-11-dev libomp5-11 lld-11 lldb-11 \
      llvm-11 llvm-11-dev llvm-11-runtime llvm-11-tools && \
    apt-get install -y gcc-9 g++-9

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 82d1c3e18dd1b90fa15f7c056f94dc1a06ee345d && \
    unset CFLAGS && unset CXXFLAGS && export LLVM_CONFIG=llvm-config-11 && \
    export REAL_CC=gcc-9 && export REAL_CXX=g++-9 && \
    AFL_NO_X86=1 CC=gcc-9 PYTHON_INCLUDE=/ make && make install && \
    make -C examples/aflpp_driver && \
    cp examples/aflpp_driver/libAFLDriver.a / && \
    cp -va `llvm-config-11 --libdir`/libc++* /afl/
