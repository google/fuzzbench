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
    apt-get install -y --no-install-recommends \
        python python3 python3-dev python3-setuptools python3-pip strace   \
        automake cmake make build-essential ninja-build gcc-9-plugin-dev   \
        libpixman-1-dev liblzma-dev libfdt-dev libncurses-dev \
        libstdc++-9-dev libglib2.0-dev zlib1g-dev libcurl4-openssl-dev     \
        curl wget subversion vim git flex bison                            \
        inotify-tools sudo lsb-release software-properties-common gnupg    \
        libfontconfig1-dev libdbus-1-dev

# Install latest Rust
RUN if which rustup; then rustup self uninstall -y; fi
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs > /rustup.sh && \
    sh /rustup.sh -y

ENV PATH="/root/.cargo/bin:${PATH}"
RUN echo PATH="$PATH:/root/.cargo/bin" >> ~/.bashrc
RUN rustup default nightly-2022-09-18

# Install LLVM
RUN cd /tmp/ &&                          \
    wget https://apt.llvm.org/llvm.sh && \
    chmod +x llvm.sh &&                  \
    ./llvm.sh 12 &&                      \
    ./llvm.sh 15

RUN update-alternatives \
    --install  /usr/lib/llvm              llvm             /usr/lib/llvm-12  20        \
    --slave    /usr/bin/llvm-config       llvm-config      /usr/bin/llvm-config-12     \
    --slave    /usr/bin/llvm-ar           llvm-ar          /usr/bin/llvm-ar-12         \
    --slave    /usr/bin/llvm-as           llvm-as          /usr/bin/llvm-as-12         \
    --slave    /usr/bin/llvm-bcanalyzer   llvm-bcanalyzer  /usr/bin/llvm-bcanalyzer-12 \
    --slave    /usr/bin/llvm-c-test       llvm-c-test      /usr/bin/llvm-c-test-12     \
    --slave    /usr/bin/llvm-cov          llvm-cov         /usr/bin/llvm-cov-12        \
    --slave    /usr/bin/llvm-diff         llvm-diff        /usr/bin/llvm-diff-12       \
    --slave    /usr/bin/llvm-dis          llvm-dis         /usr/bin/llvm-dis-12        \
    --slave    /usr/bin/llvm-dwarfdump    llvm-dwarfdump   /usr/bin/llvm-dwarfdump-12  \
    --slave    /usr/bin/llvm-extract      llvm-extract     /usr/bin/llvm-extract-12    \
    --slave    /usr/bin/llvm-link         llvm-link        /usr/bin/llvm-link-12       \
    --slave    /usr/bin/llvm-mc           llvm-mc          /usr/bin/llvm-mc-12         \
    --slave    /usr/bin/llvm-nm           llvm-nm          /usr/bin/llvm-nm-12         \
    --slave    /usr/bin/llvm-objdump      llvm-objdump     /usr/bin/llvm-objdump-12    \
    --slave    /usr/bin/llvm-ranlib       llvm-ranlib      /usr/bin/llvm-ranlib-12     \
    --slave    /usr/bin/llvm-readobj      llvm-readobj     /usr/bin/llvm-readobj-12    \
    --slave    /usr/bin/llvm-rtdyld       llvm-rtdyld      /usr/bin/llvm-rtdyld-12     \
    --slave    /usr/bin/llvm-size         llvm-size        /usr/bin/llvm-size-12       \
    --slave    /usr/bin/llvm-stress       llvm-stress      /usr/bin/llvm-stress-12     \
    --slave    /usr/bin/llvm-symbolizer   llvm-symbolizer  /usr/bin/llvm-symbolizer-12 \
    --slave    /usr/bin/llvm-tblgen       llvm-tblgen      /usr/bin/llvm-tblgen-12

RUN update-alternatives \
    --install  /usr/bin/clang             clang            /usr/bin/clang-12  20       \
    --slave    /usr/bin/clang++           clang++          /usr/bin/clang++-12         \
    --slave    /usr/bin/clang-cpp         clang-cpp        /usr/bin/clang-cpp-12

# Install AFL++.
# RUN git clone https://github.com/AFLplusplus/AFLplusplus /afl && \
#     cd /afl && git checkout 149366507da1ff8e3e8c4962f3abc6c8fd78b222

RUN echo "rerun=25"
RUN git clone https://github.com/Lukas-Dresel/AFLplusplus/ /afl-lukas && \
    cd /afl-lukas && git checkout fixed/symcts-4d


RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl-base/ && cd /afl-base/ && git checkout 8e1df8e53d359f2858168a276c46d1113d4102f2


# Prepare output dirs
RUN mkdir -p /out/afl /out/symcts /out/instrumented/symcts /out/instrumented/afl_base /out/instrumented/afl_lukas

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
# COPY src/afl_driver.cpp /afl/afl_driver.cpp
RUN cd /afl-base/ && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    make -j$(nproc) NO_NYX=1 NO_PYTHON=1 source-only && \
    make install && \
    cp utils/aflpp_driver/libAFLDriver.a /libAFLDriver-base.a && \
    cp -r /afl-base/ /afl/

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
# COPY src/afl_driver.cpp /afl/afl_driver.cpp
RUN cd /afl-lukas/ && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang CXX=clang++ AFL_NO_X86=1 && \
    (LLVM_CONFIG=llvm-config-12 make -j$(nproc) -k NO_NYX=1 NO_PYTHON=1 source-only || true ) && \
    (LLVM_CONFIG=llvm-config-12 make install -k || true) && \
    (cd utils/aflpp_driver && LLVM_CONFIG=llvm-config-12 make && cp libAFLDriver.a /libAFLDriver-lukas.a)


ENV CFLAGS=""
ENV CXXFLAGS=""

# Install Z3 from binary
# RUN apt-get update && apt-get remove -y libz3-dev
RUN mkdir -p /z3/include /z3/lib && \
    wget -qO /tmp/z3x64.zip https://github.com/Z3Prover/z3/releases/download/z3-4.8.7/z3-4.8.7-x64-ubuntu-16.04.zip && \
    unzip -ojd /z3/include /tmp/z3x64.zip "*/include/*.h" && \
    unzip -ojd /z3/lib /tmp/z3x64.zip "*/bin/libz3.so" && \
    ldconfig

ENV LIBRARY_PATH="/z3/lib/:$LIBRARY_PATH"

RUN git clone https://github.com/Lukas-Dresel/symcc.git /symcc && \
    cd /symcc && \
    git checkout fixed/symcts-4d && \
    git submodule init && \
    git submodule update

RUN mkdir /symcc/build_simple && \
    cd /symcc/build_simple && \
    cmake -DCMAKE_BUILD_TYPE=Release -DZ3_TRUST_SYSTEM_VERSION=ON ../ && \
    make -j$(nproc)

RUN mkdir /symcc/build_qsym && \
    cd /symcc/build_qsym && \
    cmake -DQSYM_BACKEND=ON -DCMAKE_BUILD_TYPE=Release -DZ3_TRUST_SYSTEM_VERSION=ON ../ && \
    make -j$(nproc)

RUN mkdir /symcc/build && \
    cd /symcc/build && \
    cmake  -DRUST_BACKEND=ON \
           -DZ3_TRUST_SYSTEM_VERSION=ON \
           -DCMAKE_BUILD_TYPE=Release \
           -DSYMCC_LIBCXX_PATH="/llvm/libcxx_symcc_install" \
           -DSYMCC_LIBCXX_INCLUDE_PATH="/llvm/libcxx_symcc_install/include/c++/v1" \
           -DSYMCC_LIBCXXABI_PATH="/llvm/libcxx_symcc_install/lib/libc++abi.a" ../ && \
    make -j$(nproc)

RUN mkdir -p /libs_symcc

ENV PATH="/usr/lib/llvm-12/bin/:$PATH"

COPY id_rsa /root/.ssh/id_rsa
RUN echo 'Host github.com\n\tStrictHostKeyChecking no\nIdentityFile ~/.ssh/id_rsa\n' >> /root/.ssh/config

# Building MCTSSE
RUN ls -l && echo rerun=4
RUN git clone -b fixed/symcts-4d --recurse-submodules git@github.com:shellphish-support-syndicate/mctsse/ /mctsse
RUN git clone -b fixed/symcts-4d --depth 1 https://github.com/Lukas-Dresel/z3jit.git /mctsse/implementation/z3jit
RUN git clone -b fixed/symcts-4d https://github.com/Lukas-Dresel/LibAFL /mctsse/repos/LibAFL

#RUN rustup install nightly-2023-06-01 && rustup default nightly-2023-06-01
RUN cd /mctsse/repos/LibAFL/libafl/ && \
    git checkout fixed/symcts-4d && \
    git pull && \
    git fetch --all && \
    echo 3 && \
    git checkout fixed/symcts-4d
COPY runtime_Cargo.lock /mctsse/implementation/libfuzzer_stb_image_symcts/runtime/Cargo.lock
COPY fuzzer_Cargo.lock /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer/Cargo.lock
RUN cd /mctsse/ && \
    git pull && git fetch --all && \
    cd /mctsse/implementation/libfuzzer_stb_image_symcts/runtime && \
    set -x && \
    echo "runtime reconfigured" && \
    cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    echo "fuzzer reconfigured"

#cargo update -p which --precise 4.4.0 && \

RUN apt-get install -y libpolly-15-dev

# RUN which llvm-config && which llvm-config-12 && which llvm-config-15 && exit 1

RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/runtime && \
    cargo build --release && \
    cp /mctsse/implementation/libfuzzer_stb_image_symcts/runtime/target/release/libSymRuntime.so /libs_symcc/
RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    rm -rf /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer/src/bin/cov_over_time.rs && \
    cargo build --release


# Build libcxx with the SymCC compiler so we can instrument C++ code.
RUN git clone -b llvmorg-12.0.0 --depth 1 https://github.com/llvm/llvm-project.git /llvm_source
RUN mkdir /libcxx_native_install && mkdir /libcxx_native_build && \
    cd /libcxx_native_install && \
    export SYMCC_REGULAR_LIBCXX="" && \
    export SYMCC_NO_SYMBOLIC_INPUT=yes && \
    export SYMCC_RUNTIME_DIR=/mctsse/implementation/libfuzzer_stb_image_symcts/runtime/target/release/ && \
    cmake /llvm_source/llvm      \
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

RUN echo rerun=1 && \
    cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    git stash && git pull && git fetch --all && git stash pop && \
    cargo build --release


# we have to build zlib instrumented because of all the callbacks being passed back and forth because SymCC does not
# (and cannot) support uninstrumented libraries calling back into instrumented code
# RUN git clone https://github.com/Lukas-Dresel/zlib-nop /zlib/ && cd /zlib && \
RUN git clone --depth=1 https://github.com/madler/zlib /zlib/ && cd /zlib && \
    export SYMCC_RUNTIME_DIR=/mctsse/implementation/libfuzzer_stb_image_symcts/runtime/target/release/ && \
    CC=/symcc/build/symcc CXX=/symcc/build/sym++ CFLAGS="-fPIC ${CFLAGS}" CXXFLAGS="-fPIC ${CXXFLAGS}" ./configure --static && \
    make -j$(nproc) && \
    cp libz.a /libs_symcc/libz.a

# RUN git clone --depth=1 https://github.com/Lukas-Dresel/symqemu "/symqemu"

# # build SymQEMU
# RUN cd "/symqemu" && \
#     mkdir -p build && \
#     export SYMCC_RUNTIME_DIR=/mctsse/implementation/libfuzzer_stb_image_symcts/runtime/target/release/ && \
#     cd /symqemu/build && \
#     ../configure                                                  \
#       --static                                                    \
#       --audio-drv-list=                                           \
#       --disable-bluez                                             \
#       --disable-sdl                                               \
#       --disable-gtk                                               \
#       --disable-vte                                               \
#       --disable-opengl                                            \
#       --disable-virglrenderer                                     \
#       --disable-werror                                            \
#       --target-list=x86_64-linux-user                             \
#       --enable-capstone=git                                       \
#       --symcc-source="/symcc/"                                    \
#       --symcc-runtime-dir="/mctsse/implementation/libfuzzer_stb_image_symcts/runtime/target/release/" && \
#     make -j$(nproc) && cp /symqemu/build/x86_64-linux-user/symqemu-x86_64 /out/


RUN git clone --depth 1 https://github.com/Lukas-Dresel/symcc_libc_preload /mctsse/repos/symcc_libc_preload
RUN cd /mctsse/repos/symcc_libc_preload && \
    make CC=/symcc/build/symcc libc_symcc_preload.a && \
    cp /mctsse/repos/symcc_libc_preload/libc_symcc_preload.a /libs_symcc/

RUN cd /mctsse/ && \
    git fetch --all && \
    git fetch origin feat/usenix-ablations && \
    git branch feat/usenix-ablations FETCH_HEAD && \
    git remote -v && \
    git branch -la && \
    git checkout feat/usenix-ablations && \
    echo 5



RUN export LLVM_CONFIG=$(which llvm-config-15) && \
    cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    cargo build --release  --bin symcts --no-default-features --features=default_fuzzbench && \
    cp ./target/release/symcts /out/symcts/symcts

RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    cargo build --release  --bin symcts --no-default-features --features=default_fuzzbench --features=scheduling_symcc && \
    cp ./target/release/symcts /out/symcts/symcts-ablation-scheduling-symcc

RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    cargo build --release  --bin symcts --no-default-features --features=default_fuzzbench --features=coverage_single_level && \
    cp ./target/release/symcts /out/symcts/symcts-ablation-coverage-edge-coverage

RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    cargo build --release  --bin symcts --no-default-features --features=default_fuzzbench --features=mutation_full_solve_first && \
    cp ./target/release/symcts /out/symcts/symcts-ablation-mutation-full-solve-first

# no sync_only_when_stuck enabled, always sync from the fuzzer immediately
RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    cargo build --release  --bin symcts --no-default-features --features=baseline,mutations_default,coverage_default,scheduling_default,sync_from_other_fuzzers && \
    cp ./target/release/symcts /out/symcts/symcts-ablation-sync-always-sync

# mimic symcc closely, edge-coverage, full-solve-first, sync when not stuck
RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    cargo build --release  --bin symcts --no-default-features --features=baseline,mutations_default,coverage_default,scheduling_default,sync_from_other_fuzzers,mutation_full_solve_first,coverage_single_level,scheduling_symcc && \
    cp ./target/release/symcts /out/symcts/symcts-ablation-symcts-as-symcc

RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    cargo build --release  --bin symcts --no-default-features --features=default_fuzzbench,resource_tracking && \
    cp ./target/release/symcts /out/symcts/symcts-ablation-resource-tracking

RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    cargo build --release  --bin symcts --no-default-features --features=default_fuzzbench,resource_tracking,resource_tracking_per_branch && \
    cp ./target/release/symcts /out/symcts/symcts-ablation-resource-tracking-per-branch

# build all the other binaries with default features
RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    cargo build --release --no-default-features --features=default_fuzzbench

RUN cd /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer && \
    /symcc/build/symcc -I/afl-lukas/include -c /afl-lukas/utils/aflpp_driver/aflpp_driver.c -o /libfuzzer-main.o /libs_symcc/libc_symcc_preload.a /libs_symcc/libz.a

# RUN rm -rf /usr/local/lib/libc++experimental.a /usr/local/lib/libc++abi.a /usr/local/lib/libc++.a && \
#     ln -s /usr/lib/llvm-10/lib/libc++abi.so.1 /usr/lib/llvm-10/lib/libc++abi.so

# Compile vanilla (uninstrumented) afl driver
RUN clang $CXXFLAGS -c -fPIC -I/afl-lukas/include \
    /afl-lukas/utils/aflpp_driver/aflpp_driver.c -o /out/instrumented/aflpp_driver.o

RUN cp /libs_symcc/libc_symcc_preload.a /out/symcts/
RUN cp /libs_symcc/libz.a /out/symcts/

RUN cp /mctsse/implementation/libfuzzer_stb_image_symcts/runtime/target/release/libSymRuntime.so /out/instrumented/symcts/
RUN cp /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer/target/release/symcts /out/instrumented/symcts
RUN cp /mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer/target/release/print_symcc_trace /out/instrumented/symcts
RUN cp /z3/lib/libz3.so /out/instrumented/symcts
RUN ln -s /out/instrumented/symcts/libz3.so /out/instrumented/symcts/libz3.so.4
RUN cp /libcxx_native_build/lib/libc++.so.1 /out/instrumented/symcts
RUN cp /libcxx_native_build/lib/libc++abi.so.1 /out/instrumented/symcts

# Remove stuff that we don't need
RUN rm -rf /mctsse /llvm_source /symqemu /root/.cache/ /root/.rustup
RUN git config --global --add safe.directory '*'

# copy the run_with_multilog.sh script to the output directory as an executable
COPY run_with_multilog.sh /out/run_with_multilog.sh
RUN chmod +x /out/run_with_multilog.sh
