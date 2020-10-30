#!/bin/bash -ex
# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

mkdir libpng-1.2.56-vani
tar xf libpng-1.2.56.tar.gz -C ./libpng-1.2.56-vani

cd libpng-1.2.56-vani/libpng-1.2.56
./configure
make -j $(nproc)

#$CXX $CXXFLAGS -std=c++11 $SRC/target.cc .libs/libpng12.a $FUZZER_LIB -I . -lz \
#    -o $OUT/libpng_read_fuzzer
$CC $CFLAGS  /buildScript/libpng-1.2.56/libpng_target.c .libs/libpng12.a /buildScript/standaloneengine.c -I . -lz \
    -o $OUT/libpng_read_fuzzer_vani
#cp -r /opt/seeds $OUT/
