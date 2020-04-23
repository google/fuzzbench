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
  automake


CXXFLAGS="${CXXFLAGS} -std=gnu++98"

build_lib() {
  rm -rf BUILD
  cp -rf SRC BUILD
  (cd BUILD && make clean && make -j $JOBS)
}

get_git_revision https://github.com/google/re2.git 499ef7eff7455ce9c9fae86111d4a77b6ac335de SRC
build_lib

$CXX $CXXFLAGS ${SCRIPT_DIR}/target.cc  -I BUILD/ BUILD/obj/libre2.a -lpthread $FUZZER_LIB -o $FUZZ_TARGET
wget -qO $FUZZ_TARGET.dict https://raw.githubusercontent.com/google/fuzzing/master/dictionaries/regexp.dict
