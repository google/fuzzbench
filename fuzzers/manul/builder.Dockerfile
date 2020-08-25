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

RUN cd / && git clone https://github.com/mxmssh/manul /manul && \
    cd /manul && sed -i "s/mutator_weights=afl:10,radamsa:0/mutator_weights=afl:3,radamsa:7/" manul_lin.config

RUN cd / && git clone https://github.com/google/AFL.git /afl && \
    cd /afl && \
    git checkout 8da80951dd7eeeb3e3b5a3bcd36c485045f40274 && \
    AFL_NO_X86=1 make

RUN apt update && apt install -y wget && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libAFL.a *.o

