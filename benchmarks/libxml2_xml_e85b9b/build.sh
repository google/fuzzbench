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

if [ "$SANITIZER" = undefined ]; then
    export CFLAGS="$CFLAGS -fsanitize=unsigned-integer-overflow -fno-sanitize-recover=unsigned-integer-overflow"
    export CXXFLAGS="$CXXFLAGS -fsanitize=unsigned-integer-overflow -fno-sanitize-recover=unsigned-integer-overflow"
fi

export V=1

./autogen.sh \
    --disable-shared \
    --without-debug \
    --without-ftp \
    --without-http \
    --without-legacy \
    --without-python
make -j$(nproc)

cd fuzz
make clean-corpus
make fuzz.o

make xml.o
# Link with $CXX
$CXX $CXXFLAGS \
    xml.o fuzz.o \
    -o $OUT/xml \
    $LIB_FUZZING_ENGINE \
    ../.libs/libxml2.a -Wl,-Bstatic -lz -llzma -Wl,-Bdynamic

[ -e seed/xml ] || make seed/xml.stamp
zip -j $OUT/xml_seed_corpus.zip seed/xml/*

cp *.dict *.options $OUT/
