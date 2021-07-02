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

FROM gcr.io/fuzzbench/base-image

RUN sed -i -- 's/# deb-src/deb-src/g' /etc/apt/sources.list && cat /etc/apt/sources.list

RUN apt update -y && \
    apt-get build-dep -y qemu-user

RUN apt install -y \
        llvm-8 clang-8 nano \
        qemu-user git libglib2.0-dev libfdt-dev \
        libpixman-1-dev zlib1g-dev libcapstone-dev \
        strace cmake python3 libprotobuf-dev libprotobuf9v5 \
        libibverbs-dev libjpeg62-dev \
        libpng16-16 libjbig-dev \
        build-essential libtool-bin python3-dev \
        automake flex bison libglib2.0-dev \
        libpixman-1-dev clang \
        python3-setuptools llvm wget \
        llvm-dev g++ g++-multilib python \
        python-pip lsb-release gcc-4.8 g++-4.8 \
        llvm-3.9 cmake libc6 libstdc++6 \
        linux-libc-dev gcc-multilib \
        apt-transport-https libtool \
        libtool-bin wget \
        automake autoconf \
        bison git valgrind ninja-build \
        time python3-pip

RUN apt clean -y

# Set environment vars for Z3
ENV C_INCLUDE_PATH=/out/fuzzolic/solver/fuzzy-sat/fuzzolic-z3/build/dist/include
ENV LIBRARY_PATH=/out/fuzzolic/solver/fuzzy-sat/fuzzolic-z3/build/dist/lib
ENV LD_LIBRARY_PATH=/out/fuzzolic/solver/fuzzy-sat/fuzzolic-z3/build/dist/lib
ENV AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES=1
ENV AFL_SKIP_CPUFREQ=1
ENV AFL_PATH=/out/AFLplusplus

