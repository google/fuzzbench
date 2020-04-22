
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
  automake \
  autoconf \
  libtool \
  sqlite3 \
  libsqlite3-dev

build_lib() {
  rm -rf BUILD
  cp -rf SRC BUILD
  (cd BUILD && ./autogen.sh &&  ./configure  &&  make clean  && make -j $JOBS )
}

get_git_revision https://github.com/OSGeo/proj.4.git d00501750b210a73f9fb107ac97a683d4e3d8e7a SRC
build_lib

if [[ ! -d $OUT/seeds ]]; then
  mkdir $OUT/seeds
  cp BUILD/nad/* $OUT/seeds
fi

$CXX $CXXFLAGS -std=c++11 -I BUILD/src BUILD/test/fuzzers/standard_fuzzer.cpp BUILD/src/.libs/libproj.a $FUZZER_LIB -o $FUZZ_TARGET -lpthread
wget -qO $FUZZ_TARGET.dict https://raw.githubusercontent.com/google/fuzzing/master/dictionaries/proj4.dict
