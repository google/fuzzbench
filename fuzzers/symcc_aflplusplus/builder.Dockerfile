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

RUN echo "deb http://archive.ubuntu.com/ubuntu bionic main universe"  >> /etc/apt/sources.list
# Install libstdc++ to use llvm_mode.
RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libtool-bin flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates libdbus-1-dev

COPY ./preinstall.sh /tmp/
RUN chmod +x /tmp/preinstall.sh
RUN /tmp/preinstall.sh
ENV PATH="/usr/bin/:{$PATH}"

# Download and compile afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 8fc249d210ad49e3dd88d1409877ca64d9884690

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && make install && \
    make -j4 -C utils/aflpp_driver && \
    cp utils/aflpp_driver/libAFLDriver.a /

# Install the packages we need.
RUN apt-get install -y ninja-build flex bison python zlib1g-dev

# RUN rm -rf /usr/local/bin/cargo

# Uninstall old Rust
RUN if which rustup; then rustup self uninstall -y; fi

# Install latest Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /rustup.sh && \
    sh /rustup.sh -y

ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup default nightly-2022-09-18


# Install Z3 from binary
RUN wget -qO /tmp/z3x64.zip https://github.com/Z3Prover/z3/releases/download/z3-4.8.7/z3-4.8.7-x64-ubuntu-16.04.zip && \
     yes | unzip -jd /usr/include /tmp/z3x64.zip "*/include/*.h" && \
     yes | unzip -jd /usr/lib /tmp/z3x64.zip "*/bin/libz3.so" && \
     rm -f /tmp/*.zip && \
     ldconfig

ENV CFLAGS=""
ENV CXXFLAGS=""

COPY adacc_atexit_not_preserving_return_code.patch /tmp/

# Get and install symcc.
RUN cd / && \
    git clone https://github.com/AdaLogics/adacc symcc && \
    cd symcc && \
    git checkout edda79dcb830c95ba6d303e47c698839313ef506 && \
    git apply /tmp/adacc_atexit_not_preserving_return_code.patch && \
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

RUN mkdir -p /rust/bin/ && cp /symcc/util/symcc_fuzzing_helper/target/release/symcc_fuzzing_helper /rust/bin/

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
