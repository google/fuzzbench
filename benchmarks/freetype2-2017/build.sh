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

apt-get update &&  \
  apt-get install -y \
  make \
  autoconf \
  libtool \
  libarchive-dev

build_lib() {
  rm -rf BUILD
  cp -rf SRC BUILD
  (cd BUILD && ./autogen.sh && ./configure --with-harfbuzz=no --with-bzip2=no --with-png=no && make clean && make all -j $JOBS)
}

get_git_revision git://git.sv.nongnu.org/freetype/freetype2.git cd02d359a6d0455e9d16b87bf9665961c4699538 SRC
build_lib

if [[ ! -d $OUT/seeds ]]; then
  mkdir $OUT/seeds
  git clone https://github.com/unicode-org/text-rendering-tests.git TRT
  # TRT/fonts is the full seed folder, but they're too big
  cp TRT/fonts/TestKERNOne.otf $OUT/seeds/
  cp TRT/fonts/TestGLYFOne.ttf $OUT/seeds/
  rm -fr TRT
fi

$CXX $CXXFLAGS -std=c++11 -I BUILD/include -I BUILD/ BUILD/src/tools/ftfuzzer/ftfuzzer.cc BUILD/objs/.libs/libfreetype.a  $FUZZER_LIB -larchive -lz -o $FUZZ_TARGET
