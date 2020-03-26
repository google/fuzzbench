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

# ************************ AFL Download and Install ****************************
# Download and compile AFL v2.56b.
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/google/AFL.git /afl && \
    cd /afl && \
    git checkout 8da80951dd7eeeb3e3b5a3bcd36c485045f40274 && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o

# *********************** AFL++ Download and Compile ***************************
# Download and compile afl++ (v2.62d).
# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /aflpp && \
    cd /aflpp && \
    git checkout 3fb346fe297ca9b33499155a1d2f486c317d9368 && \
    AFL_NO_X86=1 make PYTHON_INCLUDE=/ && \
    cd libdislocator && make && cd .. && \
    cd llvm_mode && CXXFLAGS= make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /aflpp/afl_driver.cpp && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /aflpp/afl_driver.cpp && \
    ar ru /libAFLDriver.a *.o

# *********************** AFLSmart Download and Compile ***************************
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
RUN git clone https://github.com/aflsmart/aflsmart /aflsmart && \
    cd /aflsmart && \
    git checkout df095901ea379f033d4d82345023de004f28b9a7 && \
    AFL_NO_X86=1 make

# Setup Peach.
# Set CFLAGS="" so that we don't use the CFLAGS defined in OSS-Fuzz images.
RUN cd /aflsmart && \
    wget https://sourceforge.net/projects/peachfuzz/files/Peach/3.0/peach-3.0.202-source.zip && \
    unzip peach-3.0.202-source.zip && \
    patch -p1 < peach-3.0.202.patch && \
    cd peach-3.0.202-source && \
    CC=gcc-4.4 CXX=g++-4.4 CFLAGS="" CXXFLAGS="-std=c++0x" ./waf configure && \
    CC=gcc-4.4 CXX=g++-4.4 CFLAGS="" CXXFLAGS="-std=c++0x" ./waf install

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /aflsmart/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /aflsmart/llvm_mode/afl-llvm-rt.o.c -I/aflsmart && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /aflsmart/afl_driver.cpp && \
    ar r /libAFL.a *.o

# *********************** Fairfuzz Download and Compile ***************************
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/carolemieux/afl-rb.git /fair && \
    cd /fair && \
    git checkout e529c1f1b3666ad94e4d6e7ef24ea648aff39ae2 && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /fair/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /fair/llvm_mode/afl-llvm-rt.o.c -I/fair && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /fair/afl_driver.cpp && \
    ar r /libAFL.a *.o

# *********************** Mopt Download and Compile ***************************
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/puppet-meteor/MOpt-AFL.git && \
    cd MOpt-AFL && \
    git checkout debd495b564b33e602afd7237227555850eeba93 && \
    mv MOpt-AFL\ V1.0 /mopt && \
    cd /mopt && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /mopt/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /mopt/llvm_mode/afl-llvm-rt.o.c -I/mopt && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /mopt/afl_driver.cpp && \
    ar r /libAFL.a *.o
