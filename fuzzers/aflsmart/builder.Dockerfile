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

# install AFLSmart dependencies
RUN dpkg --add-architecture i386 && \
    apt-get update -y && apt-get install -y \
    apt-utils \
    libc6-dev-i386 \
    python-pip \
    g++-multilib \
    mono-complete \
    gnupg-curl \
    software-properties-common

# install gcc-4.4 & g++-4.4 required by Peach while running on Ubuntu 16.04
RUN add-apt-repository --keyserver hkps://keyserver.ubuntu.com:443 ppa:ubuntu-toolchain-r/test -y && \
    apt-get update -y && apt-get install -y \
    gcc-4.4 \
    g++-4.4 \
    unzip \
    wget \
    tzdata

# Download and compile AFLSmart
RUN git clone https://github.com/aflsmart/aflsmart /afl && \
    cd /afl && \
    git checkout 5fb84f3b6a0ec24059958c498fc691de01bc5fcc && \
    AFL_NO_X86=1 make

# Setup Peach.
# Set CFLAGS="" so that we don't use the CFLAGS defined in OSS-Fuzz images.
# Use a copy of
# https://sourceforge.net/projects/peachfuzz/files/Peach/3.0/peach-3.0.202-source.zip
# to avoid network flakiness.
RUN cd /afl && \
    wget https://storage.googleapis.com/fuzzbench-files/peach-3.0.202-source.zip && \
    unzip peach-3.0.202-source.zip && \
    patch -p1 < peach-3.0.202.patch && \
    cd peach-3.0.202-source && \
    CC=gcc-4.4 CXX=g++-4.4 CFLAGS="" CXXFLAGS="-std=c++0x" ./waf configure && \
    CC=gcc-4.4 CXX=g++-4.4 CFLAGS="" CXXFLAGS="-std=c++0x" ./waf install

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o
