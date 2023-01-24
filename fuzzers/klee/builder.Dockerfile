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

# The following installation Steps 1-8 are from KLEE's recommended build guide:
# https://klee.github.io/build-llvm11/
# We should merge some of them to minimise Dockerfile / docker image.

# Step 1: Install dependencies.
# Install dependencies for KLEE.
RUN apt-get update && \
    apt-get install -y \
        build-essential \
        cmake \
        curl \
        file \
        g++-multilib \
        gcc-multilib \
        git \
        libcap-dev \
        libgoogle-perftools-dev \
        libncurses5-dev \
        libsqlite3-dev \
        libtcmalloc-minimal4 \
        python3-pip \
        unzip \
        graphviz \
        doxygen

# Install dependencies for testing and additional features.
RUN pip3 install lit wllvm && \
    apt-get install -y python3-tabulate
ENV PATH=$PATH:'~/.local/bin'

# Step 2: Install LLVM 11.
RUN apt-get install -y clang-11 llvm-11 llvm-11-dev llvm-11-tools
ENV PATH='/usr/lib/llvm-11/bin':$PATH
ENV LD_LIBRARY_PATH='/usr/lib/llvm-11/lib':$LD_LIBRARY_PATH
# ENV LD_LIBRARY_PATH='/usr/lib/clang/11.0.0/lib/linux':$LD_LIBRARY_PATH
# ENV LDFLAGS="$LDFLAGS -pthread"

# Step 3: Install constraint solver (STP).
# Install STP dependencies.
RUN apt-get install -y \
        cmake \
        bison \
        flex \
        libboost-all-dev \
        python \
        perl \
        zlib1g-dev \
        minisat \
        libboost-all-dev \
        perl \
        zlib1g-dev

ENV INSTALL_DIR=/out

# Install minisat.
RUN git clone https://github.com/stp/minisat.git /src/minisat && \
    mkdir /src/minisat/build && \
    (cd /src/minisat/build && \
    CXXFLAGS= cmake -DSTATIC_BINARIES=ON \
    -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR -DCMAKE_BUILD_TYPE=Release ../ && \
    make -j`nproc` && make install)

# Install STP solver.
RUN git clone \
        --depth 1 \
        --branch 2.3.3\
        https://github.com/stp/stp.git /src/stp && \
    mkdir /src/stp/build && \
    (cd /src/stp/build && \
    CXXFLAGS= cmake -DBUILD_SHARED_LIBS:BOOL=ON \
      -DENABLE_PYTHON_INTERFACE:BOOL=OFF \
      -DMINISAT_LIBRARY=$INSTALL_DIR/lib/libminisat.so.2.1.0 \
      -DMINISAT_INCLUDE_DIR=$INSTALL_DIR/include \
      -DCMAKE_INSTALL_PREFIX=/user/local/ -DCMAKE_BUILD_TYPE=Release .. && \
    make -j`nproc` && make install)

# Step 4 (Optional): Get Google test sources.
RUN curl \
        -o /src/release-1.11.0.zip \
        -L https://github.com/google/googletest/archive/release-1.11.0.zip && \
    unzip /src/release-1.11.0.zip -d /src && \
    rm /src/release-1.11.0.zip

# Step 5(Optional): Build uClibc and the POSIX environment model.
# Enable the KLEE POSIX runtime to run on real programs.
ENV KLEE_UCLIBC='/src/klee-uclibc'
RUN git clone https://github.com/klee/klee-uclibc.git $KLEE_UCLIBC && \
    (cd $KLEE_UCLIBC && \
    ./configure --make-llvm-lib && \
#        --make-llvm-lib \
#         --with-cc clang-11 \
#         --with-llvm-config llvm-config-11 && \
    make -j`nproc`)

# Step 6: Get KLEE source.
ENV KLEE_DIR=/src/klee
RUN git clone https://github.com/klee/klee.git $KLEE_DIR

# Step 7 (Optional): Build libc++.
ENV LIBCXX_DIR=/src/libcxx
RUN mkdir $LIBCXX_DIR && \
    (cd $KLEE_DIR && \
    LLVM_VERSION=11 BASE=$LIBCXX_DIR ./scripts/build/build.sh libcxx)

# Step 8: Configure KLEE.
RUN mkdir $KLEE_DIR/build && \
    (cd $KLEE_DIR/build && \
    cmake \
        -DENABLE_SOLVER_STP=ON \
        -DENABLE_POSIX_RUNTIME=ON \
        -DKLEE_UCLIBC_PATH=/src/klee-uclibc \
        -DENABLE_UNIT_TESTS=ON \
        -DLLVM_CONFIG_BINARY=/usr/bin/llvm-config-11 \
        -DGTEST_SRC_DIR=/src/googletest-release-1.11.0/ \
        -DENABLE_KLEE_LIBCXX=ON \
        -DKLEE_LIBCXX_DIR=/src/libcxx/libc++-install-110/ \
        -DKLEE_LIBCXX_INCLUDE_DIR=/src/libcxx/libc++-install-110/include/c++/v1/ \
        -DENABLE_KLEE_EH_CXX=ON \
        -DKLEE_LIBCXXABI_SRC_DIR=/src/libcxx/llvm-110/libcxxabi/ \
        ..)

# Step 9: Build KLEE.
RUN (cd $KLEE_DIR/build && \
    make)


# Install Clang/LLVM 6.0.
# RUN apt-get update -y && \
#     apt-get -y install llvm-11.0 \
#     clang-6.0 llvm-6.0-dev llvm-6.0-tools \
#     wget

# # Install KLEE.
# ENV LIBCXX_DIR=/src/libcxx
# RUN mkdir $LIBCXX_DIR && \
#     git clone https://github.com/klee/klee.git && \
#     cd klee && \
#     LLVM_VERSION=11 BASE=$LIBCXX_DIR \
#         ./scripts/build/build.sh libcxx \
#     mkdir build && \
#     cd build && \
#     cmake \
#         -DENABLE_SOLVER_STP=ON \
#         -DENABLE_POSIX_RUNTIME=ON \
#         -DKLEE_UCLIBC_PATH=/src/klee-uclibc \
#         -DENABLE_UNIT_TESTS=ON \
#         -DLLVM_CONFIG_BINARY=/usr/bin/llvm-config-11 \
#         -DGTEST_SRC_DIR=/src/googletest-release-1.11.0/ \
#         -DENABLE_KLEE_LIBCXX=ON \
#         -DKLEE_LIBCXX_DIR=/src/libcxx/libc++-install-110/ \
#         -DKLEE_LIBCXX_INCLUDE_DIR=/src/libcxx/libc++-install-110/include/c++/v1/ \
#         -DENABLE_KLEE_EH_CXX=ON \
#         -DKLEE_LIBCXXABI_SRC_DIR=/src/libcxx/llvm-110/libcxxabi/ \
#         .. && \
#     make && \
#     make systemtests && \
#     lit test/ && \
#     make unittests


# # Install libstdc++-4.8.
# RUN echo 'deb http://dk.archive.ubuntu.com/ubuntu/ trusty main' >> /etc/apt/sources.list && \
#     echo 'deb http://dk.archive.ubuntu.com/ubuntu/ trusty universe' >> /etc/apt/sources && \
#     apt-get update && \
#     apt-get install -y libstdc++-4.8-dev
#
# # Install KLEE dependencies.
# RUN apt-get install -y \
#     cmake-data build-essential curl libcap-dev \
#     git cmake libncurses5-dev unzip libtcmalloc-minimal4 \
#     libgoogle-perftools-dev bison flex libboost-all-dev \
#     perl zlib1g-dev libsqlite3-dev doxygen
#
# ENV INSTALL_DIR=/out
#
# # Install minisat.
# RUN git clone https://github.com/stp/minisat.git /minisat && \
#     cd /minisat && mkdir build && cd build && \
#     CXXFLAGS= cmake -DSTATIC_BINARIES=ON \
#     -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR -DCMAKE_BUILD_TYPE=Release ../ && \
#     make -j`nproc` && make install
#
# # Install STP solver.
# RUN git clone https://github.com/stp/stp.git /stp && \
#     cd /stp && git checkout tags/2.1.2 && \
#     mkdir build && cd build && \
#     CXXFLAGS= cmake -DBUILD_SHARED_LIBS:BOOL=OFF \
#     -DENABLE_PYTHON_INTERFACE:BOOL=OFF \
#     -DMINISAT_LIBRARY=$INSTALL_DIR/lib/libminisat.so \
#     -DMINISAT_INCLUDE_DIR=$INSTALL_DIR/include \
#     -DCMAKE_INSTALL_PREFIX=/user/local/ -DCMAKE_BUILD_TYPE=Release .. && \
#     make -j`nproc` && make install
#
# RUN git clone https://github.com/klee/klee-uclibc.git /klee-uclibc && \
#     cd /klee-uclibc && \
#     CC=`which clang-6.0` CXX=`which clang++-6.0` \
#     ./configure --make-llvm-lib --with-llvm-config=`which llvm-config-6.0` && \
#     make -j`nproc` && make install
#
# # Install KLEE. Use my personal repo containing seed conversion scripts for now.
# # TODO: Include seed conversion scripts in fuzzbench repo.
# # Note: don't use the 'debug' branch because it has checks for non-initialized values
# # that need to be fixed for certain syscalls.
# # When we use it, be sure to also use klee-uclibc from https://github.com/lmrs2/klee-uclibc.git.
# RUN git clone https://github.com/lmrs2/klee.git /klee && \
#     cd /klee && \
#     git checkout 3810917841c1cb58587719c1d3d47181a2401324 && \
#     wget -O tools/ktest-tool/ktest-tool https://raw.githubusercontent.com/lmrs2/klee/debug/tools/ktest-tool/ktest-tool
#
# # The libcxx build script in the KLEE repo depends on wllvm:
# RUN pip3 install wllvm

# # Before building KLEE, build libcxx.
# RUN cd /klee && \
#     LLVM_VERSION=6.0 SANITIZER_BUILD= ENABLE_OPTIMIZED=0 ENABLE_DEBUG=1 \
#     DISABLE_ASSERTIONS=1 REQUIRES_RTTI=1 \
#     BASE=/out \
#     ./scripts/build/build.sh libcxx
#
# RUN cd /klee &&  \
#     mkdir build && cd build && \
#     CXXFLAGS= cmake -DENABLE_SOLVER_STP=ON -DENABLE_POSIX_RUNTIME=ON \
#     -DENABLE_KLEE_LIBCXX=ON -DKLEE_LIBCXX_DIR=/out/libc++-install-60/ \
#     -DKLEE_LIBCXX_INCLUDE_DIR=/out/libc++-install-60/include/c++/v1/ \
#     -DENABLE_KLEE_UCLIBC=ON -DKLEE_UCLIBC_PATH=/klee-uclibc/ \
#     -DENABLE_SYSTEM_TESTS=OFF -DENABLE_UNIT_TESTS=OFF \
#     -DLLVM_CONFIG_BINARY=`which llvm-config-6.0` -DLLVMCC=`which clang-6.0` \
#     -DLLVMCXX=`which clang++-6.0` -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR ../ \
#     -DCMAKE_BUILD_TYPE=Release && \
#     make -j`nproc` && make install
#
# ENV LLVM_CC_NAME=clang-6.0
# ENV LLVM_CXX_NAME=clang++-6.0
# ENV LLVM_AR_NAME=llvm-ar-6.0
# ENV LLVM_LINK_NAME=llvm-link-6.0
# ENV LLVM_COMPILER=clang
# ENV CC=wllvm
# ENV CXX=wllvm++
#
# # Compile the harness klee_driver.cpp.
# COPY klee_driver.cpp /klee_driver.cpp
# COPY klee_mock.c /klee_mock.c
# RUN $CXX -stdlib=libc++ -std=c++11 -O2 -c /klee_driver.cpp -o /klee_driver.o && \
#     ar r /libAFL.a /klee_driver.o && \
#     $LLVM_CC_NAME -O2 -c -fPIC /klee_mock.c -o /klee_mock.o && \
#     $LLVM_CC_NAME -shared -o /libKleeMock.so /klee_mock.o
