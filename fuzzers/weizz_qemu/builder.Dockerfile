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

#
# When the llvm-12 installation gets LLVMgold (llvm-12-dev) then we can get
# rid of the clang-8 installation :-(
#

RUN apt-get update && \
    apt-get install -y wget libstdc++-5-dev libtool-bin automake \
            flex bison libglib2.0-dev libpixman-1-dev cmake automake \
            libglib2.0-dev libpixman-1-dev liblzma-dev \
            llvm-8-dev clang-8

RUN cd / && git clone https://github.com/andreafioraldi/weizz-fuzzer /weizz && \
    cd /weizz && \
    git checkout c9cbeef0b057b9f7dc62af9b20629090b1b9fe4f && \
    export CC=clang-8 && export CXX=clang++-8 && \
    CFLAGS="-O3 -funroll-loops" make

RUN cd / && git clone https://github.com/vanhauser-thc/qemu_driver && \
    cd /qemu_driver && \
    git checkout 8ad9ad589b4881552fa7ef8b7d29cd9aeb5071bd && \
    make && \
    cp -fv libQEMU.a /

