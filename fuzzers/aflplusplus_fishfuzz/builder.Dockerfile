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

RUN apt-get install -y libboost-all-dev libjsoncpp-dev libgraphviz-dev \
    pkg-config libglib2.0-dev findutils

RUN apt install -y lsb-release wget software-properties-common

RUN wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 12 all && \
    cp /usr/lib/llvm-12/lib/LLVMgold.so /usr/lib/bfd-plugins/ && \
    cp /usr/lib/llvm-12/lib/libLTO.so /usr/lib/bfd-plugins/

ENV LLVM_CONFIG=llvm-config-12

RUN update-alternatives \
      --install /usr/lib/llvm              llvm             /usr/lib/llvm-12  100 \
      --slave   /usr/bin/llvm-config       llvm-config      /usr/bin/llvm-config-12  \
        --slave   /usr/bin/llvm-ar           llvm-ar          /usr/bin/llvm-ar-12 \
        --slave   /usr/bin/llvm-as           llvm-as          /usr/bin/llvm-as-12 \
        --slave   /usr/bin/llvm-bcanalyzer   llvm-bcanalyzer  /usr/bin/llvm-bcanalyzer-12 \
        --slave   /usr/bin/llvm-c-test       llvm-c-test      /usr/bin/llvm-c-test-12 \
        --slave   /usr/bin/llvm-cov          llvm-cov         /usr/bin/llvm-cov-12 \
        --slave   /usr/bin/llvm-diff         llvm-diff        /usr/bin/llvm-diff-12 \
        --slave   /usr/bin/llvm-dis          llvm-dis         /usr/bin/llvm-dis-12 \
        --slave   /usr/bin/llvm-dwarfdump    llvm-dwarfdump   /usr/bin/llvm-dwarfdump-12 \
        --slave   /usr/bin/llvm-extract      llvm-extract     /usr/bin/llvm-extract-12 \
        --slave   /usr/bin/llvm-link         llvm-link        /usr/bin/llvm-link-12 \
        --slave   /usr/bin/llvm-mc           llvm-mc          /usr/bin/llvm-mc-12 \
        --slave   /usr/bin/llvm-nm           llvm-nm          /usr/bin/llvm-nm-12 \
        --slave   /usr/bin/llvm-objdump      llvm-objdump     /usr/bin/llvm-objdump-12 \
        --slave   /usr/bin/llvm-ranlib       llvm-ranlib      /usr/bin/llvm-ranlib-12 \
        --slave   /usr/bin/llvm-readobj      llvm-readobj     /usr/bin/llvm-readobj-12 \
        --slave   /usr/bin/llvm-rtdyld       llvm-rtdyld      /usr/bin/llvm-rtdyld-12 \
        --slave   /usr/bin/llvm-size         llvm-size        /usr/bin/llvm-size-12 \
        --slave   /usr/bin/llvm-stress       llvm-stress      /usr/bin/llvm-stress-12 \
        --slave   /usr/bin/llvm-symbolizer   llvm-symbolizer  /usr/bin/llvm-symbolizer-12 \
        --slave   /usr/bin/llvm-tblgen       llvm-tblgen      /usr/bin/llvm-tblgen-12 \
        --slave   /usr/bin/llc               llc              /usr/bin/llc-12 \
        --slave   /usr/bin/opt               opt              /usr/bin/opt-12 && \
    update-alternatives \
      --install /usr/bin/clang                 clang                  /usr/bin/clang-12     100 \
      --slave   /usr/bin/clang++               clang++                /usr/bin/clang++-12 \
      --slave   /usr/bin/clang-cpp             clang-cpp              /usr/bin/clang-cpp-12

# put the /usr/bin of the highest priority, to make sure clang-12 is called before clang-15, which is in /usr/local/bin
ENV PATH="/usr/bin:${PATH}"

## Download fishfuzz.
RUN git clone https://github.com/HexHive/FishFuzz/ /afl && \
    mv /afl/FF_AFL++ /FishFuzz

ENV PATH="/usr/bin/:$PATH"

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /FishFuzz/ && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    make clean && \
    rm -f ff-all-in-one ff-all-in-one++ && \
    PYTHON_INCLUDE=/ make && \
    make -C dyncfg && \
    chmod +x scripts/*.py && \
    make install

RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /FishFuzz/afl_driver.cpp && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /FishFuzz/afl_driver.cpp -o /FishFuzz/afl_driver.o && \
    ar r /libAFL.a /FishFuzz/afl_driver.o /FishFuzz/afl-compiler-rt.o
