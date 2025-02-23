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
        libstdc++-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-dev \
        lsb-release \
        software-properties-common \
        gnupg

RUN wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 15
RUN apt install llvm-15

RUN for llvmbin in $(find $(dirname $(which llvm-link-15)) | grep -- '-15$'); do \
      ln -s "$llvmbin" /usr/local/bin/$(basename "$llvmbin" | rev | cut -d'-' -f2- | rev); \
    done && \
    which llvm-link llvm-dis

RUN curl -L https://go.dev/dl/go1.23.2.linux-amd64.tar.gz | \
    tar -C /usr/local -xz

ENV PATH="$PATH:/usr/local/go/bin:/root/go/bin"

RUN go install github.com/SRI-CSL/gllvm/cmd/...@v1.3.1

# Download FOX.
RUN git clone -b dev https://github.com/FOX-Fuzz/FOX /afl && \
    cd /afl && \
    git checkout 5265de4e3762c9424127d7278ac55c42dada82ce || \
    true

COPY --chmod=755 second_stage.sh /second_stage.sh

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    cp utils/aflpp_driver/libAFLDriver.a /
