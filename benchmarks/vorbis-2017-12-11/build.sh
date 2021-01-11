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

readonly INSTALL_DIR="$PWD/INSTALL"

cd ogg
git checkout c8391c2b267a7faf9a09df66b1f7d324e9eb7766
./autogen.sh
./configure \
    --prefix="$INSTALL_DIR" \
    --enable-static \
    --disable-shared \
    --disable-crc
make -j $(nproc)
make install
cd ..

cd vorbis
git checkout c1c2831fc7306d5fbd7bc800324efd12b28d327f
./autogen.sh
./configure \
    --prefix="$INSTALL_DIR" \
    --enable-static \
    --disable-shared
make -j $(nproc)
make install
cd ..

$CXX $CXXFLAGS -std=c++11 decode_fuzzer.cc \
    -o $OUT/decode_fuzzer -L"$INSTALL_DIR/lib" -I"$INSTALL_DIR/include" \
    $FUZZER_LIB -lvorbisfile -lvorbis -logg
cp -r /opt/seeds $OUT/
