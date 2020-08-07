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

cd perl5
git checkout v5.21.7

# There are other options we might wish to toggle in future.
#  sh Configure
#     -Dafl_cc=${AFL_CC}
#     -Dcc=${LCC}
#     -Accflags="${LCFLAGS}"
#     -de
#     -Dusedevel
#     -des
#     -Aldflags="${LCFLAGS}"
#     -Alddlflags="-shared"
./Configure -des -Dusedevel
make -j $(nproc)

# To test with the main() in perl_fuzz.cc, use -D_HAS_MAIN and disable any
# fuzzer in sanitizer flag / use of FUZZER_LIB.
$CXX $CXXFLAGS -I . $SRC/perl_fuzz.cc libperl.a \
    -lnsl -ldl -lm -lcrypt -lutil -lc -lpthread \
     $FUZZER_LIB -o $OUT/fuzz-target
cp -r /opt/seeds $OUT/
