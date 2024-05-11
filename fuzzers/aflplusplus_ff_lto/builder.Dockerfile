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

# Download afl++.
RUN git clone -b dev_ff https://github.com/kdsjZh/AFLplusplus /afl && \
    cd /afl && \
    git checkout 7c196d6 || \
    true

RUN apt install lsb-release software-properties-common gnupg -y && \
    wget https://apt.llvm.org/llvm.sh && \
    chmod +x llvm.sh && ./llvm.sh 15 all 

RUN apt install python3-pip -y 

RUN pip3 install --upgrade setuptools

RUN pip3 install networkx pydot

#libcjson-dev==1.7.15
RUN wget https://github.com/DaveGamble/cJSON/archive/refs/tags/v1.7.15.tar.gz && \
    tar xf v1.7.15.tar.gz && cd cJSON-1.7.15 && sed -i 's/gcc/clang-15/g' Makefile && \ 
    make && make install && \
    cd .. && rm -r cJSON-1.7.15 v1.7.15.tar.gz

# ENV PATH=/usr/bin/:${PATH}
RUN rm /usr/local/bin/llvm-* /usr/local/bin/clang* && \
    ln -s /usr/bin/clang-15 /usr/bin/clang && \
    ln -s /usr/bin/clang++-15 /usr/bin/clang++ && \
    ln -s /usr/bin/llvm-config-15 /usr/bin/llvm-config

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang-15 AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    cp utils/aflpp_driver/libAFLDriver.a /
