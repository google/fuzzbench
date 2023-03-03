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

INSTALL_DIR="$PWD/install"

mkdir $OUT/seeds
# TRT/fonts is the full seed folder, but they're too big
cp TRT/fonts/TestKERNOne.otf $OUT/seeds/
cp TRT/fonts/TestGLYFOne.ttf $OUT/seeds/

tar xf libarchive-3.4.3.tar.xz

cd libarchive-3.4.3
./configure --prefix="$INSTALL_DIR" --disable-shared --with-xml2=no
make clean
make -j $(nproc)
make install
cd ..

cd freetype2
./autogen.sh
./configure --with-harfbuzz=no --with-bzip2=no --with-png=no --without-zlib
make clean
make all -j $(nproc)

$CXX $CXXFLAGS -std=c++11 -I"$INSTALL_DIR/include" -I include -I . src/tools/ftfuzzer/ftfuzzer.cc \
    objs/.libs/libfreetype.a $FUZZER_LIB -L"$INSTALL_DIR/lib" -larchive \
    -o $OUT/ftfuzzer
