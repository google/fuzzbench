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

# Install the necessary packages.
RUN apt-get update && \
    apt-get install -y \
        build-essential \
        git \
        flex \
        bison \
        libglib2.0-dev \
        libpixman-1-dev \
        ninja-build \
        libstdc++-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-dev


# Download afl++
RUN git clone https://github.com/AFLplusplus/AFLplusplus.git /afl && \
    cd /afl && git checkout 27d05f3c216e18163236efa42b630a5b3784d2e9 || true
    
# Build afl++ without Python support as we don't need it.
# Set AFL_NO_X86 to skip flaky tests.
RUN cd /afl && \
    unset CFLAGS && unset CXXFLAGS && \
    AFL_NO_X86=1 CC=clang PYTHON_INCLUDE=/ make && \
    cd qemu_mode && ./build_qemu_support.sh && cd .. && \
    make -C utils/aflpp_driver && \
    cp utils/aflpp_driver/libAFLQemuDriver.a /libAFLDriver.a && \
    cp utils/aflpp_driver/aflpp_qemu_driver_hook.so /
