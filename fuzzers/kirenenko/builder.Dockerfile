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

ARG parent_image=gcr.io/fuzzbench/base-builder
FROM $parent_image

# Install Clang/LLVM 6.0.
RUN apt-get update -y && \
    apt-get -y install libc6 libstdc++6  \
		linux-libc-dev linux-libc-dev gcc-multilib \
    llvm-6.0 clang-6.0 llvm-6.0-dev llvm-6.0-tools \
		llvm-dev  zlib1g-dev git cmake  python-pip \
		g++ g++-multilib wget

RUN apt-get install -y libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates


# Download and install AFL++.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout f41aafa4f7aa446c3cb1cbe6d77364cf32a6c6cb && \
    unset CFLAGS && unset CXXFLAGS && export CC=clang && \
    AFL_NO_X86=1 PYTHON_INCLUDE=/ make && make install && \
    make -C examples/aflpp_driver && \
    cp examples/aflpp_driver/libAFLDriver.a /


RUN git clone https://github.com/Z3Prover/z3.git /z3 && \
		cd /z3 && git checkout z3-4.8.7 && mkdir -p build && cd build && \
		cmake .. && make && make install
RUN ldconfig

RUN wget https://download.redis.io/releases/redis-6.0.8.tar.gz?_ga=2.106808267.950746773.1603437795-213833146.1603437795 -O /redis-6.0.8.tar.gz
RUN tar xvf /redis-6.0.8.tar.gz -C /
RUN cd /redis-6.0.8 && make && make install

RUN git clone https://github.com/redis/hiredis.git /hiredis
RUN cd /hiredis && make && make install

RUN ldconfig

RUN rm -rf /usr/local/include/llvm && rm -rf /usr/local/include/llvm-c
RUN rm -rf /usr/include/llvm && rm -rf /usr/include/llvm-c
RUN ln -s /usr/lib/llvm-6.0/include/llvm /usr/include/llvm
RUN ln -s /usr/lib/llvm-6.0/include/llvm-c /usr/include/llvm-c
RUN git clone https://github.com/ChengyuSong/Kirenenko.git  /Kirenenko
COPY kir.patch /Kirenenko/kir.patch
RUN cd /Kirenenko && git checkout 0390f27d23cd69337a1e8f31cd5cc93422107ec2  && patch -p1 < kir.patch && ./build/build.sh
RUN cd /Kirenenko/tests/mini && KO_CC=clang-6.0 KO_DONT_OPTIMIZE=1 ../../bin/ko-clang mini.c

COPY untrack.list  /untrack.list
COPY discard.list  /discard.list
RUN cat /untrack.list >> /Kirenenko/bin/rules/zlib_abilist.txt
RUN cat /discard.list >> /Kirenenko/bin/rules/zlib_abilist.txt

COPY standaloneengine.c /src

RUN pip install --upgrade pip

