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

# Install Go.
RUN mkdir -p /application
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://dl.google.com/go/go1.14.3.linux-amd64.tar.gz
RUN tar -C /application -xzf go1.14.3.linux-amd64.tar.gz

# Clone Ankou and its dependencies.
RUN /application/go/bin/go get github.com/SoftSec-KAIST/Ankou
# Compile Ankou.
RUN /application/go/bin/go build github.com/SoftSec-KAIST/Ankou

# Download and compile AFL.
# Set AFL_NO_X86 to skip flaky tests.
RUN wget http://lcamtuf.coredump.cx/afl/releases/afl-latest.tgz && \
    tar xf afl-latest.tgz && \
    mv afl-2.52b afl && \
    cd /afl && \
    AFL_NO_X86=1 make

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o
