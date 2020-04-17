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
  (cd BUILD && ./autogen.sh && ./configure && make -j $JOBS)
}

get_git_revision https://github.com/mm2/Little-CMS.git f9d75ccef0b54c9f4167d95088d4727985133c52 SRC
build_lib

$CXX $CXXFLAGS ${SCRIPT_DIR}/cms_transform_fuzzer.cc -I BUILD/include/ BUILD/src/.libs/liblcms2.a $FUZZER_LIB -o $FUZZ_TARGET
cp -r $SCRIPT_DIR/seeds $OUT/
wget -qO $FUZZ_TARGET.dict https://raw.githubusercontent.com/google/fuzzing/master/dictionaries/icc.dict
