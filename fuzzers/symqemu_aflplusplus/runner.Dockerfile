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

FROM gcr.io/fuzzbench/base-image

RUN apt-get install -y wget
RUN sed -i -- 's/# deb-src/deb-src/g' /etc/apt/sources.list
RUN echo deb http://apt.llvm.org/xenial/ llvm-toolchain-xenial-10 main >> /etc/apt/sources.list && \
    wget -O - https://apt.llvm.org/llvm-snapshot.gpg.key | apt-key add -
RUN echo deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main >> /etc/apt/sources.list && \
    apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 1E9377A2BA9EF27F
RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates

# Install the packages we need.
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

# Install Z3 from binary
RUN wget -qO /tmp/z3x64.zip https://github.com/Z3Prover/z3/releases/download/z3-4.8.7/z3-4.8.7-x64-ubuntu-16.04.zip && \
     unzip -jd /usr/include /tmp/z3x64.zip "*/include/*.h" && \
     unzip -jd /usr/lib /tmp/z3x64.zip "*/bin/libz3.so" && \
     rm -f /tmp/*.zip && \
     ldconfig

ENV CFLAGS=""
ENV CXXFLAGS=""

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

RUN cd / && git clone --depth=1 https://github.com/vanhauser-thc/adacc /symcc && \
    cd /symcc && git checkout 72b5687a6e3d1e5e477b10e77dd0047611b6b5b9

RUN cd /usr/bin && ln -s llvm-config-10 llvm-config && \
    ln -s clang-10 clang && ln -s clang++-10 clang++

RUN cd /symcc && \
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

ENV LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/out"

