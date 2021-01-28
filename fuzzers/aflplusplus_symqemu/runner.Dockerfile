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

FROM gcr.io/fuzzbench/base-image

# Install symqemu deps.
RUN sed -i -- 's/# deb-src/deb-src/g' /etc/apt/sources.list
RUN apt-get install -y wget libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev unzip \
                       apt-utils apt-transport-https ca-certificates
RUN echo deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-10 main >> /etc/apt/sources.list && \
    wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
RUN echo deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main >> /etc/apt/sources.list && \
    apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 1E9377A2BA9EF27F

RUN apt-get update -y && \
    apt-get upgrade -y && \
    apt-get install -y \
        libtool \
        wget \
        automake \
        autoconf \
        bison \
        git \
        build-essential \
        gdb \
        g++ \
        cmake \
        cargo \
        rustc \
        sudo \
        joe \
        vim \
        zlib1g \
        zlib1g-dev \
        wget \
        bison \
        flex \
        gdb \
        strace
RUN apt-get build-dep -y qemu
RUN pip3 install lit
RUN cd / && wget https://github.com/ninja-build/ninja/releases/download/v1.10.1/ninja-linux.zip && \
    unzip ninja-linux.zip && chmod 755 ninja && mv ninja /usr/local/bin && rm ninja-linux.zip
RUN apt-get install -y \
        clang-10 \
        llvm-10-dev \
        llvm-10-tools \
        libllvm10
RUN apt-get install -y gcc-9 g++-9 libstdc++-9-dev
RUN apt-get install -y libgnutls28-dev libshishi-dev libshishi0 shishi-common

ENV CC=clang-10
ENV CXX=clang++-10
ENV PATH=/usr/bin:$PATH

# Download and compile afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 3903dac1f5c0ce40965d40c956d79e46463654ea

RUN cd /afl && unset CFLAGS && unset CXXFLAGS && export AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ LLVM_CONFIG=none make && \
    make install

RUN cd / && git clone --depth=1 https://github.com/vanhauser-thc/symcc
WORKDIR /symcc

RUN wget https://github.com/Z3Prover/z3/archive/z3-4.8.9.tar.gz && \
    tar xzf z3-4.8.9.tar.gz && \
    cd z3-z3-4.8.9 && \
    mkdir build && \
    cd build && \
    cmake .. && \
    make && \
    make install

RUN ln -fs /usr/bin/llvm-config-10 /usr/bin/llvm-config && \
    git submodule update --init && \
    mkdir build && \
    cd build && \
    cmake -G Ninja -DQSYM_BACKEND=ON -DZ3_DIR=/symcc/z3-z3-4.8.9/build ..
RUN cd /symcc/build && ninja
RUN cargo install --path util/symcc_fuzzing_helper

RUN git clone --depth=1 https://github.com/eurecom-s3/symqemu
RUN cd /symcc/symqemu && \
    ./configure                                                   \
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
      --symcc-source=/symcc/                                      \
      --symcc-build=/symcc/build && \
    make

RUN cp -v /symcc/symqemu/x86_64-linux-user/symqemu-x86_64 /symcc
RUN cp -v ~/.cargo/bin/symcc_fuzzing_helper /symcc

RUN ln -sf python3.8m /usr/bin/python3m
RUN ln -sf python3.8 /usr/bin/python3

ENV AFL_MAP_SIZE=65536
ENV PATH="$PATH:/out:/symcc"
ENV AFL_SKIP_CPUFREQ=1
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
ENV AFL_TESTCACHE_SIZE=2

RUN mkdir /targets
WORKDIR /targets

