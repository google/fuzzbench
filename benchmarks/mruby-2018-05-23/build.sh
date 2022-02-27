#!/bin/bash -eu
# Copyright 2019 Google Inc.
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

# Instrument mruby
(
cd $SRC/mruby
export LD=$CC
export LDFLAGS="$CFLAGS"
rake -m || true

test -f $SRC/mruby/build/host/lib/libmruby.a

# build fuzzers
FUZZ_TARGET=$SRC/mruby_fuzzer.c
name=$(basename $FUZZ_TARGET .c)
$CC -c $CFLAGS -Iinclude \
     ${FUZZ_TARGET} -o $OUT/${name}.o
$CXX $CXXFLAGS $OUT/${name}.o $LIB_FUZZING_ENGINE -lm \
    $SRC/mruby/build/host/lib/libmruby.a -o $OUT/${name}
rm -f $OUT/${name}.o
)

# dict
cp $SRC/mruby.dict $OUT/mruby_fuzzer.dict

# seeds
zip -rq $OUT/mruby_fuzzer_seed_corpus $SRC/mruby_seeds
