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
    apt-get -y install wget python3-pip python3-setuptools apt-transport-https \
    #llvm-6.0 llvm-6.0-dev clang-6.0 llvm-6.0-tools libboost-all-dev texinfo \
    libboost-all-dev texinfo \
    lsb-release software-properties-common autoconf curl zlib1g-dev cmake protobuf-compiler



#install cargo
RUN if [ -x "$(command -v rustc)" ]; then rustup self uninstall -y; fi
RUN curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | bash -s -- -y

#RUN rustup update
#install protobuf
RUN wget https://apt.llvm.org/llvm.sh && chmod +x llvm.sh && ./llvm.sh 12




RUN rm -rf /usr/include/z3
RUN rm -rf /usr/local/include/z3
RUN mkdir -p /out/lib
RUN git clone https://github.com/Z3Prover/z3.git /z3 && \
		cd /z3 && git checkout z3-4.8.12 && mkdir -p build && cd build && \
		#cmake -DCMAKE_INSTALL_PREFIX=/out .. && make -j && make install
		CC=clang-12 CXX=clang++-12 cmake  .. && make -j && make install
RUN ldconfig


RUN git clone https://github.com/protocolbuffers/protobuf.git /protobuf  && \
    cd /protobuf && \
    git checkout f4d0f7c85eb5347b5296d44ae2ad3ba2e27e0050 && \
    git submodule update --init --recursive && \
    unset CFLAGS && \
    unset CXXFLAGS && \
    ./autogen.sh && \
    ./configure --prefix=/out && \
   # ./configure  && \
    make -j && \
    make install

RUN ldconfig


# Download and compile afl++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout e4ff0ebd56d8076abd2413ebfaeb7b5e6c07bc3a && \
    unset CFLAGS && unset CXXFLAGS && \
    export CC=clang && export AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && make install && \
    cp utils/aflpp_driver/libAFLDriver.a /


#RUN rm -rf /usr/local/include/llvm && rm -rf /usr/local/include/llvm-c
#RUN rm -rf /usr/include/llvm && rm -rf /usr/include/llvm-c
#RUN ln -s /usr/lib/llvm-6.0/include/llvm /usr/include/llvm
#RUN ln -s /usr/lib/llvm-6.0/include/llvm-c /usr/include/llvm-c
RUN cp /usr/local/lib/libz3.so.4.8.12.0 /out/lib/
ENV PATH="/out/bin:${PATH}"
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cp /usr/local/lib/libpython3.8.so.1.0 /out/
# build kirenenko

#COPY fastgen_para /out/fastgen
RUN git clone https://github.com/chenju2k6/symsan /symsan

#RUN rm /usr/local/lib/libc++*
#RUN rm -r /usr/local/include/c++
#RUN apt-get update -y
RUN apt-get install -y libc++abi-12-dev libc++-12-dev libunwind-dev
RUN cd /symsan && git checkout unified_frontend && \
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
