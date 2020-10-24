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

# Download and compile afl.
# Set AFL_NO_X86 to skip flaky tests.
RUN git clone --single-branch --branch stable https://github.com/google/AFL.git /afl && \
    cd /afl && \
    AFL_NO_X86=1 make

RUN apt-get update && apt-get install wget g++ build-essential -y

# Use StandaloneFuzzTargetMain.c from LLVM as our fuzzing library.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/master/compiler-rt/lib/fuzzer/standalone/StandaloneFuzzTargetMain.c -O /StandaloneFuzzTargetMain.c && \
    clang -O2 -c /StandaloneFuzzTargetMain.c && \
    ar rc /libNeuzz.a StandaloneFuzzTargetMain.o && \
    rm /StandaloneFuzzTargetMain.c

# Download and compile neuzz.
# Use Ammar's repo with patch for ASan and other bug fixes.
# See https://github.com/Dongdongshe/neuzz/pull/16.
RUN git clone https://github.com/ammaraskar/neuzz /neuzz && \
    cd /neuzz && \
    git checkout e93c7a4c625aa1a17ae2f99e5902d62a46eaa068 && \
    clang -O3 -funroll-loops ./neuzz.c -o neuzz
