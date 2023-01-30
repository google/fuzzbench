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

RUN apt-get update && \
    apt-get install -y \
        build-essential \
        python3-dev \
        python3-setuptools \
        automake \
        cmake \
        git \
        flex \
        bison \
        libglib2.0-dev \
        libpixman-1-dev \
        cargo \
        libgtk-3-dev \
        # for QEMU mode
        ninja-build \
        gcc-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-plugin-dev \
        libstdc++-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-dev

# Install libstdc++ to use llvm_mode.
COPY ./preinstall.sh /tmp/
RUN chmod +x /tmp/preinstall.sh
RUN /tmp/preinstall.sh

# Download afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus /afl

# Checkout a current commit
RUN cd /afl && git checkout 149366507da1ff8e3e8c4962f3abc6c8fd78b222


# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make distrib && \
    make install && \
    cp utils/aflpp_driver/libAFLDriver.a /

# Install the packages we need.
RUN apt-get update && apt-get install -y ninja-build flex bison python zlib1g-dev
RUN apt-get update && apt-get install -y vim strace

# Install libstdc++ to use llvm_mode.
# RUN apt-get update && \
#     apt-get install -y wget libstdc++-10-dev libtool-bin automake flex bison \
#                        libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
#                        apt-utils apt-transport-https ca-certificates \
#                        binutils cmake llvm llvm-dev clang libclang-dev

# RUN llvm-config

# RUN apt install -y lsb-release wget software-properties-common && wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 12

# RUN update-alternatives \
#         --install /usr/lib/llvm              llvm             /usr/lib/llvm-10  20 \
#         --slave   /usr/bin/llvm-config       llvm-config      /usr/bin/llvm-config-10  \
#         --slave   /usr/bin/llvm-ar           llvm-ar          /usr/bin/llvm-ar-10 \
#         --slave   /usr/bin/llvm-as           llvm-as          /usr/bin/llvm-as-10 \
#         --slave   /usr/bin/llvm-bcanalyzer   llvm-bcanalyzer  /usr/bin/llvm-bcanalyzer-10 \
#         --slave   /usr/bin/llvm-c-test       llvm-c-test      /usr/bin/llvm-c-test-10 \
#         --slave   /usr/bin/llvm-cov          llvm-cov         /usr/bin/llvm-cov-10 \
#         --slave   /usr/bin/llvm-diff         llvm-diff        /usr/bin/llvm-diff-10 \
#         --slave   /usr/bin/llvm-dis          llvm-dis         /usr/bin/llvm-dis-10 \
#         --slave   /usr/bin/llvm-dwarfdump    llvm-dwarfdump   /usr/bin/llvm-dwarfdump-10 \
#         --slave   /usr/bin/llvm-extract      llvm-extract     /usr/bin/llvm-extract-10 \
#         --slave   /usr/bin/llvm-link         llvm-link        /usr/bin/llvm-link-10 \
#         --slave   /usr/bin/llvm-mc           llvm-mc          /usr/bin/llvm-mc-10 \
#         --slave   /usr/bin/llvm-nm           llvm-nm          /usr/bin/llvm-nm-10 \
#         --slave   /usr/bin/llvm-objdump      llvm-objdump     /usr/bin/llvm-objdump-10 \
#         --slave   /usr/bin/llvm-ranlib       llvm-ranlib      /usr/bin/llvm-ranlib-10 \
#         --slave   /usr/bin/llvm-readobj      llvm-readobj     /usr/bin/llvm-readobj-10 \
#         --slave   /usr/bin/llvm-rtdyld       llvm-rtdyld      /usr/bin/llvm-rtdyld-10 \
#         --slave   /usr/bin/llvm-size         llvm-size        /usr/bin/llvm-size-10 \
#         --slave   /usr/bin/llvm-stress       llvm-stress      /usr/bin/llvm-stress-10 \
#         --slave   /usr/bin/llvm-symbolizer   llvm-symbolizer  /usr/bin/llvm-symbolizer-10 \
#         --slave   /usr/bin/llvm-tblgen       llvm-tblgen      /usr/bin/llvm-tblgen-10 \
#         --slave   /usr/bin/llc               llc              /usr/bin/llc-10 \
#         --slave   /usr/bin/opt               opt              /usr/bin/opt-10 && \
#     update-alternatives \
#       --install /usr/bin/clang                 clang                  /usr/bin/clang-10     20 \
#       --slave   /usr/bin/clang++               clang++                /usr/bin/clang++-10 \
#       --slave   /usr/bin/clang-cpp             clang-cpp              /usr/bin/clang-cpp-10

# RUN rm -rf /usr/local/bin/cargo

# Uninstall old Rust
RUN if which rustup; then rustup self uninstall -y; fi

# Install latest Rust
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /rustup.sh && \
    sh /rustup.sh -y

ENV PATH="/root/.cargo/bin:${PATH}"
RUN rustup default nightly-2022-09-18

ENV CFLAGS=""
ENV CXXFLAGS=""

# ENV PATH=/usr/lib/llvm-10/bin/:$PATH

# Install Z3 from binary
# RUN apt-get update && apt-get remove -y libz3-dev
RUN mkdir -p /z3/include /z3/lib && \
     wget -qO /tmp/z3x64.zip https://github.com/Z3Prover/z3/releases/download/z3-4.8.7/z3-4.8.7-x64-ubuntu-16.04.zip && \
     unzip -ojd /z3/include /tmp/z3x64.zip "*/include/*.h" && \
     unzip -ojd /z3/lib /tmp/z3x64.zip "*/bin/libz3.so" && \
     ldconfig

ENV LIBRARY_PATH="/z3/lib/:$LIBRARY_PATH"

# RUN llvm-config --cmakedir && exit 1

RUN echo "rerun 4"

RUN git clone https://github.com/Lukas-Dresel/symcc.git /symcc && \
    mkdir /symcc/build && \
    cd /symcc/build && \
        cmake -DCMAKE_BUILD_TYPE=Release -DZ3_TRUST_SYSTEM_VERSION=ON ../ && \
    make -j

# LLVM_DIR="$(llvm-config --cmakedir)" LDFLAGS="-pthread -L /usr/lib/llvm-10/lib/" CXXFLAGS="$CXXFLAGS_EXTRA --std=c++17 -pthread" \


# Build libcxx with the SymCC compiler so we can instrument
# C++ code.
RUN git clone -b llvmorg-12.0.0 --depth 1 https://github.com/llvm/llvm-project.git /llvm_source  && \
    mkdir /libcxx_native_install && mkdir /libcxx_native_build && \
    cd /libcxx_native_install && \
    export SYMCC_REGULAR_LIBCXX="" && \
    export SYMCC_NO_SYMBOLIC_INPUT=yes && \
    cmake /llvm_source/llvm                                     \
      -G Ninja \
      -DLLVM_ENABLE_PROJECTS="libcxx;libcxxabi"       \
      -DLLVM_DISTRIBUTION_COMPONENTS="cxx;cxxabi;cxx-headers"   \
      -DLLVM_TARGETS_TO_BUILD="X86" -DCMAKE_BUILD_TYPE=Release  \
      -DCMAKE_C_COMPILER=/symcc/build/symcc                     \
      -DCMAKE_CXX_COMPILER=/symcc/build/sym++                   \
      -DHAVE_POSIX_REGEX=1     \
      -DCMAKE_INSTALL_PREFIX="/libcxx_native_build" \
      -DHAVE_STEADY_CLOCK=1 && \
    ninja distribution && \
    ninja install-distribution && \
    unset SYMCC_REGULAR_LIBCXX SYMCC_NO_SYMBOLIC_INPUT

RUN mkdir -p /libs_symcc

ENV PATH="/usr/lib/llvm-12/bin/:$PATH"

RUN echo rerun=6 && git clone --depth 1 --recurse-submodules https://github.com/Lukas-Dresel/mctsse/ /mctsse
RUN git clone --depth 1 https://github.com/Lukas-Dresel/z3jit.git /mctsse/implementation/z3jit
RUN mkdir /mctsse/repos/
RUN git clone -b feat/symcts https://github.com/Lukas-Dresel/LibAFL /mctsse/repos/LibAFL

# RUN cd /mctsse/repos/LibAFL && cargo build --release

# export LLVM_CONFIG=/usr/lib/llvm-12/bin/llvm-config &&
RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/runtime && cargo build --release && cp /mctsse/implementation/libfuzzer_stb_image_symcts/runtime/target/release/libSymRuntime.so /libs_symcc/


COPY ./build_zlib.sh /build_zlib.sh
# RUN git clone https://github.com/Lukas-Dresel/zlib-nop /zlib/ && cd /zlib && \

# we have to build zlib instrumented because of all the callbacks being passed back and forth because SymCC does not
# (and cannot) support uninstrumented libraries calling back into instrumented code
RUN git clone https://github.com/madler/zlib /zlib/ && cd /zlib && \
    CC=/symcc/build/symcc CXX=/symcc/build/sym++ CFLAGS="-fPIC ${CFLAGS}" CXXFLAGS="-fPIC ${CXXFLAGS}" ./configure --static && \
    make -j && \
    cp libz.a /libs_symcc/libz.a
    # CC=/symcc/build/symcc CXX=/symcc/build/sym++ ./configure && \
    # make -j && \
    # cp libz.so /libs_symcc/zlib.so

RUN git clone --depth=1 https://github.com/Lukas-Dresel/symqemu "/symqemu"

# build SymQEMU
RUN cd "/symqemu" && \
    mkdir -p build && \
    cd /symqemu/build && \
    ../configure                                                  \
      --static                                                    \
      --audio-drv-list=                                           \
      --disable-bluez                                             \
      --disable-sdl                                               \
      --disable-gtk                                               \
      --disable-vte                                               \
      --disable-opengl                                            \
      --disable-virglrenderer                                     \
      --disable-werror                                            \
      --target-list=x86_64-linux-user                             \
      --enable-capstone=git                                       \
      --symcc-source="/symcc/"                                    \
      --symcc-runtime-dir="/mctsse/implementation/libfuzzer_stb_image_symcts/runtime/target/release" # now fixed in my fork && \
    make -j$(nproc)

# RUN git clone https://github.com/madler/zlib /zlib/ && \


RUN git clone https://github.com/Lukas-Dresel/symcc_libc_preload /mctsse/repos/symcc_libc_preload && exit 0
RUN cd /mctsse/repos/symcc_libc_preload && SYMCC_RUNTIME_DIR=/libs_symcc/ CC=/symcc/build/symcc make all
RUN ls /mctsse/repos/symcc_libc_preload/ -al && exit 0
RUN cp /mctsse/repos/symcc_libc_preload/libc_symcc_preload.a /libs_symcc/libc_symcc_preload.a

RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && cargo build --release
RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && cargo build --release --features=sync_from_other_fuzzers

RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    /symcc/build/symcc -c ./libfuzzer-main.c -o /libfuzzer-main.o /mctsse/repos/symcc_libc_preload/libc_symcc_preload.a /libs_symcc/libz.a

# RUN rm -rf /usr/local/lib/libc++experimental.a /usr/local/lib/libc++abi.a /usr/local/lib/libc++.a && \
#     ln -s /usr/lib/llvm-10/lib/libc++abi.so.1 /usr/lib/llvm-10/lib/libc++abi.so

