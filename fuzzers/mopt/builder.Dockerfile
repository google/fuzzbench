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

# Set AFL_NO_X86 to skip flaky tests.
RUN git clone https://github.com/puppet-meteor/MOpt-AFL /afl && \
    cd /afl && \
    git checkout 45b9f38d2d8b699fd571cfde1bf974974339a21e && \
    cd MOpt && AFL_NO_X86=1 make && \
    cp afl-fuzz ..

# Use afl_driver.cpp from LLVM as our fuzzing library.
RUN apt-get update && \
    apt-get install wget -y && cd /afl/MOpt && \
    wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/afl/afl_driver.cpp -O /afl/MOpt/afl_driver.cpp && \
    clang -Wno-pointer-sign -c -o /afl/MOpt/afl-llvm-rt.o /afl/MOpt/llvm_mode/afl-llvm-rt.o.c -I/afl/MOpt && \
    clang++ -stdlib=libc++ -std=c++11 -O2 -c -o /afl/MOpt/afl_driver.o /afl/MOpt/afl_driver.cpp && \
    ar r /libAFL.a *.o
