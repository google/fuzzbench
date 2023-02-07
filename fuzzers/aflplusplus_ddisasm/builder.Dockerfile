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

RUN apt-get update && \
    apt-get install -y \
    build-essential \
    python3-dev \
    python3-setuptools \
    automake \
    cmake \
    git \
    flex \
    bison \
    libglib2.0-dev \
    libpixman-1-dev \
    cargo \
    libgtk-3-dev \
    libbz2-dev \
    # for QEMU mode
    ninja-build \
    gcc-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-plugin-dev \
    libstdc++-$(gcc --version|head -n1|sed 's/\..*//'|sed 's/.* //')-dev


# Download afl++.
RUN cd /src && git clone -b dev https://github.com/AFLplusplus/AFLplusplus afl

# Checkout a current commit
RUN cd /src/afl && git checkout 5163a49350ed17149cb3c52bc79bd87e86402510 || true

RUN apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/standalone/StandaloneFuzzTargetMain.c -O /StandaloneFuzzTargetMain.c && \
    clang -O2 -c /StandaloneFuzzTargetMain.c && \
    ar rc /libStandaloneFuzzTarget.a StandaloneFuzzTargetMain.o && \
    rm /StandaloneFuzzTargetMain.c


RUN cd /src/afl && \
    unset CFLAGS CXXFLAGS && \
    export CC=clang AFL_NO_X86=1 && \
    PYTHON_INCLUDE=/ make && \
    make install && \
    cp utils/aflpp_driver/libAFLDriver.a /


RUN wget -O - https://download.grammatech.com/gtirb/files/apt-repo/conf/apt.gpg.key | apt-key add -
RUN echo "deb https://download.grammatech.com/gtirb/files/apt-repo focal stable"| tee -a /etc/apt/sources.list

RUN apt-get update && apt-get install -y libgtirb gtirb-pprinter ddisasm

RUN pip3 install --upgrade pip
RUN pip3 install gtirb


# docker build -f builder.Dockerfile -t aflplusplus_ddisasm .
# docker run -ti --rm -v $(pwd):/workdir aflplusplus_ddisasm:latest
