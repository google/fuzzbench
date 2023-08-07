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

ARG DEBIAN_FRONTEND=noninteractive

RUN apt update && \
    apt install -y \
    silversearcher-ag beanstalkd gdb screen patchelf apt-transport-https ca-certificates clang-9 libclang-9-dev\
    gcc-7 g++-7 sudo curl wget build-essential make cmake ninja-build git subversion python3 python3-dev python3-pip autoconf automake &&\
    python3 -m pip install --upgrade pip && python3 -m pip install greenstalk psutil

RUN update-alternatives --install /usr/bin/clang clang /usr/bin/clang-9 10 \
                        --slave /usr/bin/clang++ clang++ /usr/bin/clang++-9 \
                        --slave /usr/bin/opt opt /usr/bin/opt-9
RUN update-alternatives --install /usr/lib/llvm llvm /usr/lib/llvm-9 20 \
                        --slave /usr/bin/llvm-config llvm-config /usr/bin/llvm-config-9 \
                        --slave /usr/bin/llvm-link llvm-link /usr/bin/llvm-link-9


RUN apt-get -y install locales && locale-gen en_US.UTF-8
ENV LC_ALL="en_US.UTF-8"

# Download and compile SieveFuzz
RUN git clone https://github.com/HexHive/SieveFuzz /afl && \
    cd /afl && \
    git checkout 1751673ed6c56b7dc69b71ef07ace49867e3cfa4 && \
    cd third_party && ./install_svf.sh

RUN  cd /afl/third_party && unset CFLAGS CXXFLAGS && \
     export CC=clang AFL_NO_X86=1 && \
     PYTHON_INCLUDE=/ && ./install_sievefuzz.sh

RUN cp -r /afl/gllvm_bins /afl/third_party/SVF/Release-build/bin


# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/third_party/sievefuzz/afl_driver.cpp && \
    cd /afl/third_party/sievefuzz && \
    clang -D AF -D TRACE_METRIC -Wno-pointer-sign -c llvm_mode/afl-llvm-rt.o.c -I. -Iinclude && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c afl_driver.cpp && \
    ar r /libAFL.a *.o


