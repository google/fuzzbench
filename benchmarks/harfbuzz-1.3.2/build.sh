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

apt-get update && \
  apt-get install -y \
  make \
  autoconf \
  automake \
  libtool \
  ragel \
  pkg-config \
  libcairo2-dev

get_git_revision https://github.com/behdad/harfbuzz.git  f73a87d9a8c76a181794b74b527ea268048f78e3 SRC

build_lib() {
  rm -rf BUILD
  cp -rf SRC BUILD
  (cd BUILD && ./autogen.sh && CCLD="$CXX $CXXFLAGS" ./configure --enable-static --disable-shared &&
    make -j $JOBS -C src fuzzing)
}

build_lib

if [[ ! -d $OUT/seeds ]]; then
  mkdir $OUT/seeds
  cp BUILD/test/shaping/fonts/sha1sum/* $OUT/seeds/
fi

$CXX $CXXFLAGS -std=c++11 -I BUILD/src/ BUILD/test/fuzzing/hb-fuzzer.cc BUILD/src/.libs/libharfbuzz-fuzzing.a $FUZZER_LIB -lglib-2.0 -o $FUZZ_TARGET
