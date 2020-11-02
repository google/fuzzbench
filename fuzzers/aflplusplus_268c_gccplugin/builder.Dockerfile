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

# Install wget to download afl_driver.cpp. Install libstdc++ to use llvm_mode.
RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libtool-bin automake flex bison \
                       libglib2.0-dev libpixman-1-dev python3-setuptools unzip \
                       apt-utils apt-transport-https ca-certificates

RUN apt-get install -y wget libstdc++-5-dev libexpat1-dev && \
    apt-get install -y apt-utils apt-transport-https ca-certificates && \
    echo deb http://ppa.launchpad.net/ubuntu-toolchain-r/test/ubuntu xenial main && \
    apt-key adv --recv-keys --keyserver keyserver.ubuntu.com 1E9377A2BA9EF27F && \
    apt-get update && \
    apt-get install -y gcc-9 g++-9 gcc-9-plugin-dev

# Download and compile afl++ (v2.62d).
# Build without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && \
    git checkout ee206da3897fd2d9f72206c3c5ea0e3fab109001 && \
    unset CFLAGS && unset CXXFLAGS && export CC=clang && \
    AFL_NO_X86=1 PYTHON_INCLUDE=/ make && \
    CC=gcc-9 CXX=g++-9 make -C gcc_plugin && \
    make -C llvm_mode && make install && \
    make -C examples/aflpp_driver && \
    cp examples/aflpp_driver/libAFLDriver.a /
