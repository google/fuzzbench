# Copyright 2021 Google LLC
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

# Download and compile AFL v2.56b.
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/google/AFL.git /afl && \
    cd /afl && \
    git checkout 8da80951dd7eeeb3e3b5a3bcd36c485045f40274 && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o

RUN sed -i -- 's/# deb-src/deb-src/g' /etc/apt/sources.list
RUN apt-get update && \
    apt-get install -y cmake cargo ninja-build flex bison && \
    apt-get build-dep -y --no-install-recommends qemu

ENV CC clang
ENV CXX clang++

RUN git clone -b z3-4.8.7 https://github.com/Z3Prover/z3.git /z3_src && \
    cd /z3_src && \
    mkdir build && \
    cd build && \
    cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/z3 .. && \
    ninja && \
    ninja install && \
    cd / && \
    rm -rf /z3_src

# We need libLLVMSupport, but the version in /usr/local/lib was built against
# libstdc++ and thus won't work with our libc++ build. We compile a new version
# that uses libc++.
RUN mkdir /llvm && \
  git clone -b llvmorg-10.0.0 --depth 1 https://github.com/llvm/llvm-project.git /llvm/src && \
  mkdir /llvm/build && \
  cd /llvm/build && \
  cmake -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_INSTALL_PREFIX=/llvm/install \
    -DLLVM_TARGETS_TO_BUILD=$(llvm-config --targets-built) \
    -DLLVM_ENABLE_LIBCXX=ON \
    -DLLVM_DISTRIBUTION_COMPONENTS="LLVMDemangle;LLVMSupport;llvm-config;llvm-headers;cmake-exports" \
    ../src/llvm && \
  ninja distribution && \
  ninja install-distribution && \
  cd /llvm && \
  rm -rf src build

RUN git clone https://github.com/eurecom-s3/symcc --depth 1 /symcc/src && \
    cd /symcc/src && \
    git submodule init && \
    git submodule update

RUN mkdir /symcc/build && \
    cd /symcc/build && \
    cmake -G Ninja \
      -DCMAKE_BUILD_TYPE=Release \
      -DQSYM_BACKEND=ON \
      -DZ3_DIR=/z3/lib/cmake/z3 \
      -DLLVM_DIR=/llvm/install/lib/cmake/llvm \
      ../src && \
    ninja && \
    cd /symcc/src && \
    cargo install --path util/symcc_fuzzing_helper

RUN git clone https://github.com/eurecom-s3/symqemu --depth 1 /symqemu/src
RUN mkdir /symqemu/build && \
    cd /symqemu/build && \
    ../src/configure                                              \
      --audio-drv-list=                                           \
      --disable-bluez                                             \
      --disable-sdl                                               \
      --disable-gtk                                               \
      --disable-vte                                               \
      --disable-opengl                                            \
      --disable-virglrenderer                                     \
      --target-list=x86_64-linux-user                             \
      --enable-capstone=git                                       \
      --disable-werror                                            \
      --symcc-source=/symcc/src                                   \
      --symcc-build=/symcc/build  && \
    make && \
    cd /symqemu && \
    rm -rf src
