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

ARG parent_image=gcr.io/fuzzbench/base-builder
FROM $parent_image

# Install wget to download afl_driver.cpp. Install libstdc++ to use llvm_mode.
#    sed -i 's/https:/http:/g' /etc/apt/sources.list /etc/apt/sources.list.d/* && \
RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libexpat1-dev && \
    apt-get install -y apt-utils apt-transport-https ca-certificates && \
    echo deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial main >> /etc/apt/sources.list && \
    echo deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main >> /etc/apt/sources.list && \
    wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add - && \
    apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 1E9377A2BA9EF27F && \
    apt-get update && \
    apt-get install -y clang-11 clang-11-doc clang-11-examples clangd-11 clang-format-11 clang-tidy-11 clang-tools-11 libc++1-11 libc++-11-dev libc++abi1-11 libc++abi-11-dev libclang1-11 libclang-11-dev libclang-common-11-dev libclang-cpp11 libclang-cpp11-dev libfuzzer-11-dev liblld-11 liblld-11-dev liblldb-11 liblldb-11-dev libllvm11 libomp-11-dev libomp-11-doc libomp5-11 lld-11 lldb-11 llvm-11 llvm-11-dev llvm-11-runtime llvm-11-tools && \
    apt-get install -y gcc-9 g++-9

# Download and compile afl++ (v2.62d).
# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout b920cd2f236c26e6dcc1231b5121b04d0bc3f650 && \
    sed -i 's/.*define MAP_SIZE_POW2.*/#define MAP_SIZE_POW2 20/g' include/config.h && \
    AFL_NO_X86=1 CFLAGS= CXXFLAGS= make PYTHON_INCLUDE=/ && \
    export LLVM_CONFIG=llvm-config-11 && \
    cd llvm_mode && CFLAGS= CXXFLAGS= REAL_CC=gcc-9 REAL_CXX=g++-9 make && \
    make install

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar ru /libAFLDriver.a *.o && \
    cp -a `llvm-config-11 --libdir`/libc++* /afl/
