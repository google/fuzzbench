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

. $(dirname $0)/../common.sh

[ ! -e libpng-1.2.56.tar.gz ] && wget https://downloads.sourceforge.net/project/libpng/libpng12/older-releases/1.2.56/libpng-1.2.56.tar.gz
[ ! -e libpng-1.2.56 ] && tar xf libpng-1.2.56.tar.gz

build_lib() {
  rm -rf BUILD
  cp -rf libpng-1.2.56 BUILD
  (cd BUILD && ./configure &&  make -j $JOBS)
}

build_lib

$CXX $CXXFLAGS -std=c++11 $SRC/target.cc BUILD/.libs/libpng12.a $FUZZER_LIB -I BUILD/ -I BUILD -lz -o $OUT/fuzz-target
cp -r /opt/seeds $OUT/
wget -qO fuzz-target.dict https://raw.githubusercontent.com/google/fuzzing/master/dictionaries/png.dict
