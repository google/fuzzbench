# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# # http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#ARG parent_image=gcr.io/fuzzbench/base-builder
ARG parent_image
FROM $parent_image

RUN apt-get update -y &&  \
    apt-get -y install wget python3-dev python3-setuptools apt-transport-https \
    libboost-all-dev texinfo libz3-dev \
    build-essential automake flex bison libglib2.0-dev libpixman-1-dev libgtk-3-dev ninja-build libnl-genl-3-dev \
    lsb-release software-properties-common autoconf curl zlib1g-dev cmake protobuf-compiler libprotobuf-dev

RUN if [ -x "$(command -v rustc)" ]; then rustup self uninstall -y; fi
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | bash -s -- -y

RUN wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 12

# Download and compile afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout 33eba1fc5652060e8d877b02135fce2325813d0c && \
    unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && make install && \
    cp utils/aflpp_driver/libAFLDriver.a /

ENV PATH="/out/bin:${PATH}"
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cp /usr/local/lib/libpython3.8.so.1.0 /out/

RUN git clone https://github.com/chenju2k6/symsan /symsan

RUN apt-get install -y libc++abi-12-dev libc++-12-dev libunwind-dev

RUN cd /symsan && git checkout jigsaw && \
    unset CFLAGS && \
    unset CXXFLAGS && \
    mkdir build && \
    cd build && \
    CC=clang-12 CXX=clang++-12 cmake -DCMAKE_INSTALL_PREFIX=. ../ && \
    make -j && make install && \
    cd ../fuzzer/cpp_core && mkdir build && cd build && cmake .. && make -j && \
    cd ../../../ && cargo build --release && \
    cp target/release/libruntime_fast.a build/lib/symsan

COPY libfuzz-harness-proxy.c /
RUN KO_DONT_OPTIMIZE=1 USE_TRACK=1 KO_CC=clang-12 KO_USE_FASTGEN=1 /symsan/build/bin/ko-clang -c /libfuzz-harness-proxy.c -o /libfuzzer-harness.o
RUN KO_DONT_OPTIMIZE=1 KO_CC=clang-12 /symsan/build/bin/ko-clang -c /libfuzz-harness-proxy.c -o /libfuzzer-harness-fast.o
