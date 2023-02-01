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

cd harfbuzz
git checkout f73a87d9a8c76a181794b74b527ea268048f78e3
./autogen.sh
(cd ./src/hb-ucdn && CCLD="$CXX $CXXFLAGS" make)
CCLD="$CXX $CXXFLAGS" ./configure --enable-static --disable-shared \
    --with-glib=no --with-cairo=no
make -j $(nproc) -C src fuzzing

mkdir $OUT/seeds
cp test/shaping/fonts/sha1sum/* $OUT/seeds/

$CXX $CXXFLAGS -std=c++11 -I src/ test/fuzzing/hb-fuzzer.cc \
    src/.libs/libharfbuzz-fuzzing.a $FUZZER_LIB -o $OUT/hb-shape-fuzzer
