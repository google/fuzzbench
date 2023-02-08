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

for f in font.cc normalize.cc transform.cc woff2_common.cc woff2_dec.cc \
         woff2_enc.cc glyph.cc table_tags.cc variable_length.cc woff2_out.cc; do
  $CXX $CXXFLAGS -std=c++11 -I ../brotli/dec -I ../brotli/enc -c src/$f &
done

for f in ../brotli/dec/*.c ../brotli/enc/*.cc; do
  $CXX $CXXFLAGS -c $f &
done

wait

$CXX $CXXFLAGS *.o $FUZZER_LIB $SRC/target.cc -I src \
    -o $OUT/convert_woff2ttf_fuzzer
