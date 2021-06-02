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
    git checkout 82b5e359463238d790cadbe2dd494d6a4928bff3 && \
    AFL_NO_X86=1 make

## Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o


# Install the packages we need.
RUN apt-get install -y ninja-build flex bison python zlib1g-dev cargo 

# Install Z3 from binary
RUN wget -qO /tmp/z3x64.zip https://github.com/Z3Prover/z3/releases/download/z3-4.8.7/z3-4.8.7-x64-ubuntu-16.04.zip && \
     unzip -jd /usr/include /tmp/z3x64.zip "*/include/*.h" && \
     unzip -jd /usr/lib /tmp/z3x64.zip "*/bin/libz3.so" && \
     rm -f /tmp/*.zip && \
     ldconfig

ENV CFLAGS=""
ENV CXXFLAGS=""

# Get and install symcc.
RUN cd / && \
    git clone https://github.com/AdaLogics/adacc symcc && \
    cd symcc && \
    git checkout edda79dcb830c95ba6d303e47c698839313ef506 && \
    cd ./runtime/qsym_backend && \
    git clone https://github.com/adalogics/qsym && \
    cd qsym && \
    git checkout adalogics && \
    cd /symcc && \
    mkdir build && \
    cd build && \
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
