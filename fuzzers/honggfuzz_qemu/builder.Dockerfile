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

# Honggfuzz requires libbfd and libunwid.
RUN apt-get update -y && \
    apt-get install -y \
    libbfd-dev \
    libunwind-dev \
    libblocksruntime-dev \
    libstdc++-5-dev libtool-bin automake \
    flex bison libglib2.0-dev libpixman-1-dev \
    liblzma-dev

# Download honggfuz version 2.1 + 8e76143f884cefd3054e352eccc09d550788dba0
# Set CFLAGS use honggfuzz's defaults except for -mnative which can build CPU
# dependent code that may not work on the machines we actually fuzz on.
# Create an empty object file which will become the FUZZER_LIB lib (since
# honggfuzz doesn't need this when hfuzz-clang(++) is used).
RUN cd / && git clone https://github.com/google/honggfuzz.git /honggfuzz && \
    cd /honggfuzz && \
    git checkout 8e76143f884cefd3054e352eccc09d550788dba0 && \
    CFLAGS="-O3 -funroll-loops" make && \
    unset CFLAGS && unset CXXFLAGS && \
    cd qemu_mode && export LIBS=-ldl && TARGETS=x86_64-linux-user make && \
    sed -i 's/-Werror //g' honggfuzz-qemu/config-host.mak && \
    cd honggfuzz-qemu && make

RUN cd / && git clone https://github.com/vanhauser-thc/qemu_driver && \
    cd /qemu_driver && \
    git checkout 499134f3aa34ce9c3d7f87f33b1722eec6026362 && \
    make && \
    cp -fv libQEMU.a /
