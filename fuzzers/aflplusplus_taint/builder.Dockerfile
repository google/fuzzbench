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
    apt-get install -y wget libstdc++-5-dev libtool-bin automake \
                       flex bison libglib2.0-dev libpixman-1-dev \
                       python2.7-dev python2.7

# Get afl++ taint
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && git checkout a8346a2412a9ebe9a77a40da70cde840b8e6157d && \
    unset CFLAGS && unset CXXFLAGS && \
    AFL_NO_X86=1 CC=clang PYTHON_INCLUDE=/ make && \
    CC=clang make -C llvm_mode  && \
    make -C examples/aflpp_driver && \
    cp examples/aflpp_driver/libAFLDriver.a / && \
    cd qemu_taint && export TAINT_BUILD_OPTIONS=--python=/usr/bin/python2.7 && \
    ./build_qemu_taint.sh
