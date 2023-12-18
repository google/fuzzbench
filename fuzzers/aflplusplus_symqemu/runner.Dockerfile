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

RUN sed -i 's/# deb/deb/' /etc/apt/sources.list

RUN apt-get update || true

RUN apt-get install -y wget libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates

RUN apt-get install -y ninja-build python zlib1g-dev cargo 

RUN apt-get install -y \
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

RUN git clone --depth=1 https://github.com/eurecom-s3/symcc

RUN apt-get install -y clang-12 llvm-12
ENV CC=clang-12
ENV CXX=clang++-12

RUN cd /symcc && git submodule update --init && \
    mkdir build && \
    cd build && \
    cmake -G Ninja -DQSYM_BACKEND=ON -DZ3_TRUST_SYSTEM_VERSION=on .. && \
    ninja

RUN cd /symcc && git clone --depth=1 https://github.com/eurecom-s3/symqemu

RUN cd /symcc/symqemu && \
    ./configure                                                   \
      --audio-drv-list=                                           \
      --disable-bluez                                             \
      --disable-sdl                                               \
      --disable-gtk                                               \
      --disable-vte                                               \
      --disable-opengl                                            \
      --disable-virglrenderer                                     \
      --target-list=x86_64-linux-user                             \
      --disable-werror                                            \
      --enable-capstone=git                                       \
      --symcc-source=/symcc/                                      \
      --symcc-build=/symcc/build && \
    make -j$(nproc)

# This makes interactive docker runs painless:
ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/out"
#ENV AFL_MAP_SIZE=2621440
ENV PATH="$PATH:/out:/symcc/symqemu/x86_64-linux-user"
ENV AFL_SKIP_CPUFREQ=1
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
ENV AFL_TESTCACHE_SIZE=2

