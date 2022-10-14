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

# Includes latest clang
ARG parent_image
FROM $parent_image

# Prerequisits

RUN apt-get update && \
    apt-get -y install git build-essential cmake ninja-build \
    python-dev \
    wget

ENV CC=gcc
ENV CXX=g++

# Compile & Install llvm 6.0.0
RUN mkdir /workdir && cd /workdir && \
    wget https://releases.llvm.org/6.0.0/llvm-6.0.0.src.tar.xz && \
    wget https://releases.llvm.org/6.0.0/cfe-6.0.0.src.tar.xz && \
    wget https://releases.llvm.org/6.0.0/compiler-rt-6.0.0.src.tar.xz && \
    wget https://releases.llvm.org/6.0.0/clang-tools-extra-6.0.0.src.tar.xz && \
    tar -xf llvm-6.0.0.src.tar.xz && mv llvm-6.0.0.src llvm6 && \
    tar -xf cfe-6.0.0.src.tar.xz && mv cfe-6.0.0.src llvm6/tools/clang && \
    tar -xf compiler-rt-6.0.0.src.tar.xz && mv compiler-rt-6.0.0.src llvm6/projects/compiler-rt && \
    tar -xf clang-tools-extra-6.0.0.src.tar.xz && mv clang-tools-extra-6.0.0.src llvm6/tools/clang/tools/extra

RUN cd /workdir && mkdir build6 && unset CFLAGS && unset CXXFLAGS && \
    cd build6 && \
    cmake -G "Ninja" -DLLVM_ENABLE_ASSERTIONS=On -DCMAKE_BUILD_TYPE=Release ../llvm6 && \
    ninja && \
    ninja install

# Compile TortoiseFuzz
ENV CC=clang
ENV CXX=clang++

RUN cd /workdir && \
    git clone https://github.com/TortoiseFuzz/TortoiseFuzz.git && \
    cd TortoiseFuzz && \
    unset CFLAGS && unset CXXFLAGS && make

# Use afl_driver.cpp from LLVM as our libFuzzer harness.
RUN  \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /workdir/TortoiseFuzz/afl_driver.cpp && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /workdir/TortoiseFuzz/afl_driver.cpp && \
    ar r /libAFLDriver.a afl_driver.o
