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
    apt-get install wget libstdc++-5-dev libtool-bin automake -y && \
    apt-get install flex bison libglib2.0-dev libpixman-1-dev -y

# Download and compile AFL, since Eclipser now adopts AFL as its random
# fuzzing module. Set AFL_NO_X86 to skip flaky tests.
RUN cd / && git clone https://github.com/google/AFL.git /afl && \
    cd /afl && \
    git checkout 8da80951dd7eeeb3e3b5a3bcd36c485045f40274 && \
    AFL_NO_X86=1 make && \
    unset CFLAGS && unset CXXFLAGS && \
    cd qemu_mode && ./build_qemu_support.sh


RUN cd / && git clone https://github.com/vanhauser-thc/qemu_driver && \
    cd /qemu_driver && \
    git checkout 8ad9ad589b4881552fa7ef8b7d29cd9aeb5071bd && \
    make && \
    cp -fv libQEMU.a /libAFLDriver.a

# Use StandaloneFuzzTargetMain.c for Eclipser.
RUN wget https://raw.githubusercontent.com/llvm/llvm-project/5feb80e748924606531ba28c97fe65145c65372e/compiler-rt/lib/fuzzer/standalone/StandaloneFuzzTargetMain.c -O /StandaloneFuzzTargetMain.c && \
    clang -O2 -c /StandaloneFuzzTargetMain.c && \
    ar rc /libStandaloneFuzzTarget.a StandaloneFuzzTargetMain.o && \
    rm /StandaloneFuzzTargetMain.c