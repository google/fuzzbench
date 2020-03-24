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
  (cd BUILD && \
    ./autogen.sh && \
    CCLD="$CXX $CXXFLAGS" ./configure --without-python && \
    make -j $JOBS
  )
}

get_git_tag https://gitlab.gnome.org/GNOME/libxml2.git v2.9.2 SRC
get_git_revision https://github.com/google/afl f10d601b3f3026461c669251696e6f1328ce6c00 afl
build_lib

$CXX $CXXFLAGS -std=c++11 $SCRIPT_DIR/target.cc -I BUILD/include BUILD/.libs/libxml2.a $FUZZER_LIB -lz -o $FUZZ_TARGET
cp afl/dictionaries/xml.dict $FUZZ_TARGET.dict
