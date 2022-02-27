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

# Install libstdc++ to use llvm_mode.
RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates

# Download and compile afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 8fc249d210ad49e3dd88d1409877ca64d9884690

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && make install && \
    make -C utils/aflpp_driver && \
    cp utils/aflpp_driver/libAFLDriver.a /

# Install the packages we need.
RUN apt-get install -y ninja-build flex bison python zlib1g-dev cargo 

# Install Z3 from binary
RUN wget -qO /tmp/z3x64.zip https://github.com/Z3Prover/z3/releases/download/z3-4.8.7/z3-4.8.7-x64-ubuntu-16.04.zip && \
     unzip -jd /usr/include /tmp/z3x64.zip "*/include/*.h" && \
     unzip -jd /usr/lib /tmp/z3x64.zip "*/bin/libz3.so" && \
     rm -f /tmp/*.zip && \
     ldconfig

# Get and install symcc.
RUN cd / && \
    git clone https://github.com/adalogics/adacc symcc && \
    cd symcc && \
    git checkout 70efb3ef512a12b31caedcfcd9c0890813cd797e && \
    cd ./runtime/qsym_backend && \
    git clone https://github.com/adalogics/qsym && \
    cd qsym && \
    git checkout adalogics && \
    cd /symcc && \
    mkdir build && \
    cd build && \
    unset CFLAGS && unset CXXFLAGS && \
    cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DQSYM_BACKEND=ON \
          -DZ3_TRUST_SYSTEM_VERSION=ON ../ && \
    ninja -j 3 && \
    cd ../examples && \
    export SYMCC_PC=1 && \
    ../build/symcc -c ./libfuzz-harness-proxy.c -o /libfuzzer-harness.o && \
    cd ../ && echo "[+] Installing cargo now 4" && \
    cargo install --path util/symcc_fuzzing_helper

# Build libcxx with the SymCC compiler so we can instrument 
# C++ code.
RUN git clone -b llvmorg-12.0.0 --depth 1 https://github.com/llvm/llvm-project.git /llvm_source  && \
    mkdir /libcxx_native_install && mkdir /libcxx_native_build && \
    cd /libcxx_native_install \
    && export SYMCC_REGULAR_LIBCXX="" && \
    unset CFLAGS && unset CXXFLAGS && \
    cmake /llvm_source/llvm                                     \
      -G Ninja  -DLLVM_ENABLE_PROJECTS="libcxx;libcxxabi"       \
      -DLLVM_DISTRIBUTION_COMPONENTS="cxx;cxxabi;cxx-headers"   \
      -DLLVM_TARGETS_TO_BUILD="X86" -DCMAKE_BUILD_TYPE=Release  \
      -DCMAKE_C_COMPILER=/symcc/build/symcc                     \
      -DCMAKE_CXX_COMPILER=/symcc/build/sym++                   \
      -DHAVE_POSIX_REGEX=1     \
      -DCMAKE_INSTALL_PREFIX="/libcxx_native_build" \
      -DHAVE_STEADY_CLOCK=1 && \
    ninja distribution && \
    ninja install-distribution 

ENV SYMCC_NO_SYMBOLIC_INPUT=1
ENV SYMCC_SILENT=1
