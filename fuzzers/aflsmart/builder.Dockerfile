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

# install AFLSmart dependencies
RUN dpkg --add-architecture i386 && \
    apt-get update -y && \
    apt-get install apt-utils -y && \
    apt-get install build-essential -y && \
    apt-get install automake -y && \
    apt-get install libtool -y && \
    apt-get install libc6-dev-i386 -y && \
    apt-get install python-pip -y && \
    apt-get install g++-multilib -y && \
    apt-get install mono-complete -y && \
    apt-get install gnupg-curl -y && \
    apt-get install software-properties-common -y 

# install gcc-4.4 required by Peach running on Ubuntu 16.04
RUN add-apt-repository --keyserver hkps://keyserver.ubuntu.com:443 ppa:ubuntu-toolchain-r/test -y && \
    apt-get update -y && \
    apt-get install gcc-4.4 -y && \
    apt-get install g++-4.4 -y && \
    apt-get install git -y && \
    apt-get install wget -y && \
    apt-get install unzip -y && \
    apt-get install tzdata -y

# Download and compile AFLSmart
RUN git clone https://github.com/aflsmart/aflsmart /afl && \
    cd afl && \
    AFL_NO_X86=1 make

# setup Peach
RUN cd /afl && \
    wget https://sourceforge.net/projects/peachfuzz/files/Peach/3.0/peach-3.0.202-source.zip && \
    unzip peach-3.0.202-source.zip && \
    patch -p1 < peach-3.0.202.patch && \
    cd peach-3.0.202-source && \
    CC=gcc-4.4 CXX=g++-4.4 CXXFLAGS="-std=c++0x" ./waf configure && \
    CC=gcc-4.4 CXX=g++-4.4 CXXFLAGS="-std=c++0x" ./waf install

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o
