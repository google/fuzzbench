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

RUN apt-get install -y python-software-properties software-properties-common && \
    add-apt-repository ppa:git-core/ppa -y && \
    apt-get update && \
    apt-get install git -y

# Add and compile AFLChurn
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/aflchurn/aflchurn.git /afl && \
    cd /afl && \ 
    AFL_NO_X86=1 make && \
    INITIAL_CXXFLAGS=$CXXFLAGS && \
    INITIAL_CFLAGS=$CFLAGS && \
    unset CFLAGS CXXFLAGS && \
    cd llvm_mode && \
    make && \
    CXXFLAGS=$INITIAL_CXXFLAGS && \
    CFLAGS=$INITIAL_CFLAGS

# Use afl_driver.cpp from LLVM as our fuzzing library.
# clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o
