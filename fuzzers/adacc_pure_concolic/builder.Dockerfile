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

# Install the packages we need
RUN apt-get install -y ninja-build flex bison python zlib1g-dev
RUN pip3 install lit filecheck

# Install Z3 from source
RUN git clone -b z3-4.8.7 https://github.com/Z3Prover/z3.git /z3_src &&  \
    cd /z3_src && \
    mkdir build && \
    cd build && \
    cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=/z3 .. && \
    ninja && \
    ninja install && \
    cd / && rm -rf /z3_src

ENV CFLAGS="-g"
ENV CXXFLAGS="-g"

# Get and install symcc
RUN git clone https://github.com/adalogics/adacc /symcc && \
    cd /symcc/runtime/qsym_backend && \
    git clone https://github.com/adalogics/qsym && \
    cd qsym && \
    git checkout adalogics && \
    cd /symcc && \
    mkdir build && \
    cd build && \
    cmake -G Ninja -DCMAKE_BUILD_TYPE=Release -DQSYM_BACKEND=ON \
          -DZ3_TRUST_SYSTEM_VERSION=ON ../ && \
    ninja && \
    cd ../examples && \
    ../build/symcc -c ./libfuzz-harness-proxy.c -o /libfuzzer-harness.o

# Build libcxx with the SymCC compiler so we can instrument 
# C++ code.
RUN git clone -b llvmorg-12.0.0 --depth 1 https://github.com/llvm/llvm-project.git /llvm_source  && \
    mkdir /libcxx_native_install && mkdir /libcxx_native_build && \
    cd /libcxx_native_install \
    && export SYMCC_REGULAR_LIBCXX="" && \
    cmake /llvm_source/llvm                                     \
      -G Ninja  -DLLVM_ENABLE_PROJECTS="libcxx;libcxxabi"       \
      -DLLVM_DISTRIBUTION_COMPONENTS="cxx;cxxabi;cxx-headers"   \
      -DLLVM_TARGETS_TO_BUILD="X86" -DCMAKE_BUILD_TYPE=Release  \                
      -DCMAKE_C_COMPILER=/symcc/build/symcc                     \
      -DCMAKE_CXX_COMPILER=/symcc/build/sym++                   \
      -DCMAKE_VERBOSE_MAKEFILE:BOOL=ON -DHAVE_POSIX_REGEX=1     \
      -DCMAKE_INSTALL_PREFIX="/libcxx_native_build" \
      -DHAVE_STEADY_CLOCK=1 && \
    ninja distribution && \
    ninja install-distribution && ls -la /libcxx_native_build 
