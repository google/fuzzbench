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

RUN sed -i -- 's/# deb-src/deb-src/g' /etc/apt/sources.list && cat /etc/apt/sources.list

RUN apt update -y && \
    apt-get build-dep -y qemu-user

RUN apt-get install -y wget libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates

# Why do some build images have ninja, other not? Weird.
RUN cd / && wget https://github.com/ninja-build/ninja/releases/download/v1.10.1/ninja-linux.zip && \
    unzip ninja-linux.zip && chmod 755 ninja && mv ninja /usr/local/bin

RUN git clone https://github.com/season-lab/fuzzolic /out/fuzzolic && \
    cd /out/fuzzolic && \
    git checkout 2c5e423aa38d9cf0692e4e812ec33b9e8c6beaa0

RUN cd /out/fuzzolic && \
    git submodule init && \
    git submodule update

RUN cd /out/fuzzolic/solver/fuzzy-sat && git fetch && \
    git submodule sync && git submodule update --init

# Download and compile afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /out/AFLplusplus && \
    cd /out/AFLplusplus && \
    git checkout 28e6b96276066a69482fdb17b38a71ba98abd700

ENV CC=clang
ENV CXX=clang++

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /out/AFLplusplus && unset CFLAGS && unset CXXFLAGS && \
    export AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    make -C utils/aflpp_driver && \
    cp utils/aflpp_driver/libAFLDriver.a / && \
    make install


RUN cd / && git clone https://github.com/vanhauser-thc/qemu_driver && \
    cd /qemu_driver && \
    git checkout 499134f3aa34ce9c3d7f87f33b1722eec6026362 && \
    make && \
    cp -fv libQEMU.a /libStandaloneFuzzTarget.a

RUN cp /out/fuzzolic/utils/afl-showmap /out && \
    cp /out/fuzzolic/utils/afl-showmap /out/AFLplusplus/ && \
    cp /out/fuzzolic/utils/afl-qemu-trace /out/ && \
    cp /out/fuzzolic/utils/afl-qemu-trace /out/AFLplusplus/ && \
    cp /out/fuzzolic/utils/merge_bitmap /out/ && \
    cp /out/fuzzolic/utils/merge_bitmap /out/AFLplusplus/

RUN apt install -y \
        llvm-8 clang-8 nano \
        qemu-user git libglib2.0-dev libfdt-dev \
        libpixman-1-dev zlib1g-dev libcapstone-dev \
        strace cmake python3 libprotobuf-dev libprotobuf9v5 \
        libibverbs-dev libjpeg62-dev \
        libpng16-16 libjbig-dev \
        build-essential libtool-bin python3-dev \
        automake flex bison libglib2.0-dev \
        libpixman-1-dev clang \
        python3-setuptools llvm wget \
        llvm-dev g++ g++-multilib python \
        python-pip lsb-release gcc-4.8 g++-4.8 \
        llvm-3.9 cmake libc6 libstdc++6 \
        linux-libc-dev gcc-multilib \
        apt-transport-https libtool \
        libtool-bin wget \
        automake autoconf \
        bison git valgrind ninja-build \
        time python3-pip
# dumb-init xxd libprotobuf10

RUN apt clean -y

ENV CFLAGS="-O3 -g -funroll-loops -Wno-error"
ENV CXXFLAGS="-O3 -g -funroll-loops -Wno-error"
RUN pip install --user virtualenv
RUN python3 -m pip install --user pytest

# Build QEMU tracer
RUN cd /out/fuzzolic/tracer && ./configure --prefix=`pwd`/../build --target-list=x86_64-linux-user && make -j 

# Build custom Z3
RUN cd /out/fuzzolic/solver/fuzzy-sat/fuzzolic-z3 && mkdir build && cd build && cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_INSTALL_PREFIX=`pwd`/dist && make -j && make install

# Set environment vars for Z3
ENV C_INCLUDE_PATH=/out/fuzzolic/solver/fuzzy-sat/fuzzolic-z3/build/dist/include
ENV LIBRARY_PATH=/out/fuzzolic/solver/fuzzy-sat/fuzzolic-z3/build/dist/lib
ENV LD_LIBRARY_PATH=/out/fuzzolic/solver/fuzzy-sat/fuzzolic-z3/build/dist/lib

# Create fuzzy-sat-CLI folder
RUN cd /out/fuzzolic/solver/fuzzy-sat && \
    git rev-parse HEAD > /tmp/revision && \
    git checkout master && \
    git submodule update && \
    cd ../.. && \
    cp -r solver/fuzzy-sat solver/fuzzy-sat-cli && \
    rm solver/fuzzy-sat-cli/.git && \
    cd solver/fuzzy-sat && \
    git checkout `cat /tmp/revision` && \
    git submodule update

# Build fuzzy-sat-CLI
RUN cd /out/fuzzolic/solver/fuzzy-sat-cli && make -j

# Build fuzzy-sat
RUN cd /out/fuzzolic/solver/fuzzy-sat && make -j

ENV CFLAGS="-O3 -g -funroll-loops -Wno-error -Wl,--allow-multiple-definition"
ENV CXXFLAGS="-O3 -g -funroll-loops -Wno-error -Wl,--allow-multiple-definition"

# Build solver frontend
RUN cd /out/fuzzolic/solver && cmake . && make -j

# Fix fuzzolic
RUN sed -i 's/FROM_FILE/READ_FD_0/' /out/fuzzolic/fuzzolic/executor.py
