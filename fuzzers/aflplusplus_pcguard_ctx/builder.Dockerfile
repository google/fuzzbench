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
    apt-get install -y wget libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates \
                       golang binutils

RUN wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 10

RUN update-alternatives \
      --install /usr/lib/llvm              llvm             /usr/lib/llvm-10  20 \
      --slave   /usr/bin/llvm-config       llvm-config      /usr/bin/llvm-config-10  \
        --slave   /usr/bin/llvm-ar           llvm-ar          /usr/bin/llvm-ar-10 \
        --slave   /usr/bin/llvm-as           llvm-as          /usr/bin/llvm-as-10 \
        --slave   /usr/bin/llvm-bcanalyzer   llvm-bcanalyzer  /usr/bin/llvm-bcanalyzer-10 \
        --slave   /usr/bin/llvm-c-test       llvm-c-test      /usr/bin/llvm-c-test-10 \
        --slave   /usr/bin/llvm-cov          llvm-cov         /usr/bin/llvm-cov-10 \
        --slave   /usr/bin/llvm-diff         llvm-diff        /usr/bin/llvm-diff-10 \
        --slave   /usr/bin/llvm-dis          llvm-dis         /usr/bin/llvm-dis-10 \
        --slave   /usr/bin/llvm-dwarfdump    llvm-dwarfdump   /usr/bin/llvm-dwarfdump-10 \
        --slave   /usr/bin/llvm-extract      llvm-extract     /usr/bin/llvm-extract-10 \
        --slave   /usr/bin/llvm-link         llvm-link        /usr/bin/llvm-link-10 \
        --slave   /usr/bin/llvm-mc           llvm-mc          /usr/bin/llvm-mc-10 \
        --slave   /usr/bin/llvm-nm           llvm-nm          /usr/bin/llvm-nm-10 \
        --slave   /usr/bin/llvm-objdump      llvm-objdump     /usr/bin/llvm-objdump-10 \
        --slave   /usr/bin/llvm-ranlib       llvm-ranlib      /usr/bin/llvm-ranlib-10 \
        --slave   /usr/bin/llvm-readobj      llvm-readobj     /usr/bin/llvm-readobj-10 \
        --slave   /usr/bin/llvm-rtdyld       llvm-rtdyld      /usr/bin/llvm-rtdyld-10 \
        --slave   /usr/bin/llvm-size         llvm-size        /usr/bin/llvm-size-10 \
        --slave   /usr/bin/llvm-stress       llvm-stress      /usr/bin/llvm-stress-10 \
        --slave   /usr/bin/llvm-symbolizer   llvm-symbolizer  /usr/bin/llvm-symbolizer-10 \
        --slave   /usr/bin/llvm-tblgen       llvm-tblgen      /usr/bin/llvm-tblgen-10 \
        --slave   /usr/bin/llc               llc              /usr/bin/llc-10 \
        --slave   /usr/bin/opt               opt              /usr/bin/opt-10 && \
    update-alternatives \
      --install /usr/bin/clang                 clang                  /usr/bin/clang-10     20 \
      --slave   /usr/bin/clang++               clang++                /usr/bin/clang++-10 \
      --slave   /usr/bin/clang-cpp             clang-cpp              /usr/bin/clang-cpp-10

RUN mkdir -p /dupfunc_ctx && cd /dupfunc_ctx && \
    wget https://andreafioraldi.github.io/assets/dupfunc_ctx.tar.gz && \
    tar xvf dupfunc_ctx.tar.gz && unset CFLAGS && unset CXXFLAGS && \
    LLVM_CONFIG=llvm-config-10 ./build.sh && rm dupfunc_ctx.tar.gz

ENV GOPATH /go
ENV PATH="/go/bin:/dupfunc_ctx/bin/:${PATH}"
ENV LLVM_COMPILER_PATH=/usr/lib/llvm-10/bin

RUN mkdir /go && go get github.com/SRI-CSL/gllvm/cmd/...

# Download and compile afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 5dd35f5281afec0955c08fe9f99e3c83222b7764 && \
    sed -i 's|^#define CMPLOG_SOLVE|// #define CMPLOG_SOLVE|' include/config.h

# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make LLVM_CONFIG=llvm-config-10 && make install

RUN cd / && gclang -I /afl/include -c /afl/utils/aflpp_driver/aflpp_driver.c && \
    ar ru libAFLDriver.a aflpp_driver.o
