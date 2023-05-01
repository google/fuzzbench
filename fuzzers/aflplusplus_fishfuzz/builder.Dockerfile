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

ENV DEBIAN_FRONTEND=noninteractive
ENV TZ=Etc/UTC

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

RUN apt install -y git gcc g++ make cmake wget \
        libgmp-dev libmpfr-dev texinfo bison python3

RUN apt install -y lsb-release wget software-properties-common

RUN wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 12 && \
    cp /usr/lib/llvm-12/lib/LLVMgold.so /usr/lib/bfd-plugins/ && \
    cp /usr/lib/llvm-12/lib/libLTO.so /usr/lib/bfd-plugins/

ENV LLVM_CONFIG=llvm-config-12

# Download afl++.
RUN git clone -b dev https://github.com/AFLplusplus/AFLplusplus /afl && \
    cd /afl && \
    git checkout d822181467ec41f1ee2d840c3c5b1918c72ffc86 || \
    true

COPY FF_AFL++ /FishFuzz 

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /FishFuzz/ && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    make -C dyncfg && \
    make install && \
    cp utils/aflpp_driver/libAFLDriver.a /libAFL.a
