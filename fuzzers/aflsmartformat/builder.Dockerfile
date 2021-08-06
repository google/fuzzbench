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

# install dependencies
RUN apt-get update && \
    apt-get install -y \
    automake \
    zlib1g-dev \
    wget && \
    pip3 install py010parser six intervaltree

# Download and compile FormatFuzzer
RUN git clone https://github.com/uds-se/FormatFuzzer.git /FormatFuzzer && \
    cd /FormatFuzzer && \
    git checkout 482098dd366236ff019bfbd75db0f142edf315be

# Download and compile AFLSmart
RUN git clone https://github.com/uds-se/aflsmart.git /afl && \
    cd /afl && \
    git checkout a39140ec836277a7612a868a4dd187fc44b6ed56 && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o
