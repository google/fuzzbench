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
  libglib2.0-dev

build_lib() {
  rm -rf BUILD
  cp -rf SRC BUILD
  (cd BUILD && \
    ./autogen.sh && \
    CCLD="$CXX $CXXFLAGS" ./configure --without-python --with-threads=no --with-zlib=no --with-lzma=no && \
    make -j $JOBS
  )
}

get_git_tag https://gitlab.gnome.org/GNOME/libxml2.git v2.9.2 SRC
build_lib

$CXX $CXXFLAGS -std=c++11 $SCRIPT_DIR/target.cc -I BUILD/include BUILD/.libs/libxml2.a $FUZZER_LIB -o $FUZZ_TARGET
wget https://raw.githubusercontent.com/google/AFL/debe27037b9444bbf090a0ffbd5d24889bb887ae/dictionaries/xml.dict -O $FUZZ_TARGET.dict
