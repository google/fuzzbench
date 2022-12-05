
# Copyright 2021 Google LLC
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

# Install and setup clang-11 for AFL/NEUZZ.
RUN apt install -y clang-11 && \
    ln -s /usr/bin/clang-11 /usr/bin/clang && \
    ln -s /usr/bin/clang++-11 /usr/bin/clang++
ENV PATH="/usr/bin:${PATH}"
ENV LD_LIBRARY_PATH="/usr/lib/clang/11.0.0/lib/linux:${LD_LIBRARY_PATH}"

# Download and compile AFL v2.56b.
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/google/AFL.git /afl && \
    cd /afl && \
    git checkout 82b5e359463238d790cadbe2dd494d6a4928bff3 && \
    AFL_NO_X86=1 make

# Download and compile neuzz.
# Use Ammar's repo with patch for ASan and other bug fixes.
# See https://github.com/Dongdongshe/neuzz/pull/16.
RUN git clone https://github.com/ammaraskar/neuzz.git /neuzz && \
    cd /neuzz && \
    git checkout e93c7a4c625aa1a17ae2f99e5902d62a46eaa068 && \
    clang -O3 -funroll-loops ./neuzz.c -o neuzz

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get update && \
    apt-get install wget -y && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/afl_driver.cpp && \
    clang -Wno-pointer-sign -c /afl/llvm_mode/afl-llvm-rt.o.c -I/afl && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c /afl/afl_driver.cpp && \
    ar r /libNeuzz.a *.o

