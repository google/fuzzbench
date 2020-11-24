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

# Install Clang/LLVM 6.0.
RUN apt-get update -y && \
    apt-get -y install llvm-6.0 \
    clang-6.0 llvm-6.0-dev llvm-6.0-tools \
    wget

# Install KLEE dependencies.
RUN apt-get install -y \
    cmake-data build-essential curl libcap-dev \
    git cmake libncurses5-dev python-minimal \
    python-pip unzip libtcmalloc-minimal4 \
    libgoogle-perftools-dev bison flex libboost-all-dev \
    perl zlib1g-dev libsqlite3-dev doxygen

ENV INSTALL_DIR=/out

# Install minisat.
RUN git clone https://github.com/stp/minisat.git /minisat && \
    cd /minisat && mkdir build && cd build && \
    CXXFLAGS= cmake -DSTATIC_BINARIES=ON \
    -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR -DCMAKE_BUILD_TYPE=Release ../ && \
    make -j`nproc` && make install

# Install STP solver.
RUN git clone https://github.com/stp/stp.git /stp && \
    cd /stp && git checkout tags/2.1.2 && \
    mkdir build && cd build && \
    CXXFLAGS= cmake -DBUILD_SHARED_LIBS:BOOL=OFF \
    -DENABLE_PYTHON_INTERFACE:BOOL=OFF \
    -DMINISAT_LIBRARY=$INSTALL_DIR/lib/libminisat.so \
    -DMINISAT_INCLUDE_DIR=$INSTALL_DIR/include \
    -DCMAKE_INSTALL_PREFIX=/user/local/ -DCMAKE_BUILD_TYPE=Release .. && \
    make -j`nproc` && make install

RUN git clone https://github.com/klee/klee-uclibc.git /klee-uclibc && \
    cd /klee-uclibc && \
    CC=`which clang-6.0` CXX=`which clang++-6.0` \
    ./configure --make-llvm-lib --with-llvm-config=`which llvm-config-6.0` && \
    make -j`nproc` && make install


# Install KLEE. Use my personal repo containing seed conversion scripts for now.
# TODO: Include seed conversion scripts in fuzzbench repo.
# Note: don't use the 'debug' branch because it has checks for non-initialized values
# that need to be fixed for certain syscalls.
# When we use it, be sure to also use klee-uclibc from https://github.com/lmrs2/klee-uclibc.git.
RUN git clone https://github.com/lmrs2/klee.git /klee && \
    cd /klee && \
    git checkout 3810917841c1cb58587719c1d3d47181a2401324 && \
    wget -O tools/ktest-tool/ktest-tool https://raw.githubusercontent.com/lmrs2/klee/debug/tools/ktest-tool/ktest-tool

# The libcxx build script in the KLEE repo depends on wllvm:
# We'll upgrade pip first to avoid a build error with the old version of pip.
RUN pip install --upgrade pip
RUN pip install wllvm

# Before building KLEE, build libcxx.
RUN cd /klee && \
    LLVM_VERSION=6.0 SANITIZER_BUILD= ENABLE_OPTIMIZED=0 ENABLE_DEBUG=1 \
    DISABLE_ASSERTIONS=1 REQUIRES_RTTI=1 \
    BASE=/out \
    ./scripts/build/build.sh libcxx

RUN cd /klee &&  \
    mkdir build && cd build && \
    CXXFLAGS= cmake -DENABLE_SOLVER_STP=ON -DENABLE_POSIX_RUNTIME=ON \
    -DENABLE_KLEE_LIBCXX=ON -DKLEE_LIBCXX_DIR=/out/libc++-install-60/ \
    -DKLEE_LIBCXX_INCLUDE_DIR=/out/libc++-install-60/include/c++/v1/ \
    -DENABLE_KLEE_UCLIBC=ON -DKLEE_UCLIBC_PATH=/klee-uclibc/ \
    -DENABLE_SYSTEM_TESTS=OFF -DENABLE_UNIT_TESTS=OFF \
    -DLLVM_CONFIG_BINARY=`which llvm-config-6.0` -DLLVMCC=`which clang-6.0` \
    -DLLVMCXX=`which clang++-6.0` -DCMAKE_INSTALL_PREFIX=$INSTALL_DIR ../ \
    -DCMAKE_BUILD_TYPE=Release && \
    make -j`nproc` && make install

ENV LLVM_CC_NAME=clang-6.0
ENV LLVM_CXX_NAME=clang++-6.0
ENV LLVM_AR_NAME=llvm-ar-6.0
ENV LLVM_LINK_NAME=llvm-link-6.0
ENV LLVM_COMPILER=clang
ENV CC=wllvm
ENV CXX=wllvm++

# Compile the harness klee_driver.cpp.
COPY klee_driver.cpp /klee_driver.cpp
COPY klee_mock.c /klee_mock.c
RUN $CXX -stdlib=libc++ -std=c++11 -O2 -c /klee_driver.cpp -o /klee_driver.o && \
    ar r /libAFL.a /klee_driver.o && \
    $LLVM_CC_NAME -O2 -c -fPIC /klee_mock.c -o /klee_mock.o && \
    $LLVM_CC_NAME -shared -o /libKleeMock.so /klee_mock.o

