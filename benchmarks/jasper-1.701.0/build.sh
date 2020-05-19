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
  (cd BUILD && ./configure --enable-static --disable-shared && make)
}

# XXX There is no hash to check. Git repo for this only goes back to 1.9x.
ZIPURL=https://www.ece.uvic.ca/~frodo/jasper/software/jasper-1.701.0.zip
rm -rf SRC jasper-1.701.0 jasper-1.701.0.zip
wget ${ZIPURL} || (printf "wget failed" && exit 1)
unzip jasper-1.701.0.zip || (printf "unzip failed" && exit 1)
mv jasper-1.701.0 SRC

build_lib

# To test with the main() in jasper_fuzz.cc, use -D_HAS_MAIN and disable any
# fuzzer in sanitizer flag / use of FUZZER_LIB.
$CXX $CXXFLAGS -std=c++11 -IBUILD/src/libjasper/include  \
  ${SCRIPT_DIR}/jasper_fuzz.cc   \
  BUILD/src/libjasper/.libs/libjasper.a $FUZZER_LIB -o $FUZZ_TARGET
cp -r $SCRIPT_DIR/seeds $OUT/
