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

build_lib() {
  rm -rf BUILD
  cp -rf SRC BUILD
# Leaving for historical.. there are other options we might wish to toggle.
#  sh Configure
#     -Dafl_cc=${AFL_CC}
#     -Dcc=${LCC} 
#     -Accflags="${LCFLAGS}"  
#     -de
#     -Dusedevel
#     -des
#     -Aldflags="${LCFLAGS}"
#     -Alddlflags="-shared"
  (cd BUILD && ./Configure -des -Dusedevel && make)
}

get_git_tag https://github.com/Perl/perl5.git v5.21.7 SRC
build_lib
# To test with the main() in perl_fuzz.cc, use -D_HAS_MAIN and disable any
# fuzzer in sanitizer flag / use of FUZZER_LIB.
$CXX $CXXFLAGS                                \
  -IBUILD                                     \
  ${SCRIPT_DIR}/perl_fuzz.cc                  \
  BUILD/libperl.a                             \
  -lnsl -ldl -lm -lcrypt -lutil -lc -lpthread \
  $FUZZER_LIB  -o $FUZZ_TARGET 
cp -r $SCRIPT_DIR/seeds $OUT/
