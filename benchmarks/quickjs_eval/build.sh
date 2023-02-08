#!/bin/bash -eu
# Copyright 2020 Google Inc.
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
#
################################################################################

# to not crash for every input...
export CFLAGS="$CFLAGS -fno-sanitize=integer-divide-by-zero,float-divide-by-zero,shift,array-bounds"

# build quickjs
# Makefile should honor CC and AR
sed -i -e 's/CC=/CC?=/' Makefile
sed -i -e 's/AR=/AR?=/' Makefile
# Makefile should not override CFLAGS
sed -i -e 's/CFLAGS=/CFLAGS+=/' Makefile
CONFIG_CLANG=y make libquickjs.a

# seeds
zip -r $OUT/fuzz_eval_seed_corpus.zip tests/*.js
zip -r $OUT/fuzz_eval_seed_corpus.zip examples/*.js

# dict
cp $SRC/js.dict $OUT/fuzz_eval.dict

cd ..
FUZZ_TARGETS="fuzz_eval"
for f in $FUZZ_TARGETS; do
    $CC $CFLAGS -Iquickjs -c $f.c -o $f.o
    $CXX $CXXFLAGS $f.o -o $OUT/$f quickjs/libquickjs.a $LIB_FUZZING_ENGINE
done
