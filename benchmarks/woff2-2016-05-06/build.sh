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

# Get seeds.
get_git_revision https://github.com/google/oss-fuzz.git e8ffee4077b59e35824a2e97aa214ee95d39ed13 oss-fuzz
mkdir -p $OUT/seeds
cp oss-fuzz/projects/woff2/corpus/* $OUT/seeds

get_git_revision https://github.com/google/woff2.git  9476664fd6931ea6ec532c94b816d8fbbe3aed90 SRC
get_git_revision https://github.com/google/brotli.git 3a9032ba8733532a6cd6727970bade7f7c0e2f52 BROTLI

rm -f *.o
for f in font.cc normalize.cc transform.cc woff2_common.cc woff2_dec.cc woff2_enc.cc glyph.cc table_tags.cc variable_length.cc woff2_out.cc; do
  $CXX $CXXFLAGS -std=c++11  -I BROTLI/dec -I BROTLI/enc -c SRC/src/$f &
done
for f in BROTLI/dec/*.c BROTLI/enc/*.cc; do
  $CXX $CXXFLAGS -c $f &
done
wait

$CXX $CXXFLAGS *.o $FUZZER_LIB $SRC/target.cc -I SRC/src -o $OUT/fuzz-target
