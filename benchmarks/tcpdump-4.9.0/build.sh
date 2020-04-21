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

#
# tcpdump really wants libpcap to share the same parent directory.
# 
mkdir SRC
get_git_tag https://github.com/the-tcpdump-group/libpcap.git  libpcap-1.9.0 SRC/libpcap
get_git_tag https://github.com/the-tcpdump-group/tcpdump.git  tcpdump-4.9.0 SRC/tcpdump


build_lib() {
  rm -rf BUILD
  cp -rf SRC BUILD
  (cd BUILD/libpcap && ./configure && make && 
   cd ../tcpdump && ./configure && make)
}

build_lib

$CXX $CXXFLAGS -std=c++11 -IBUILD/libpcap -IBUILD/tcpdump  \
  ${SCRIPT_DIR}/tcpdump_fuzz.cc BUILD/libpcap/libpcap.a  \
  BUILD/tcpdump/libnetdissect.a $FUZZER_LIB -o $FUZZ_TARGET
cp -r $SCRIPT_DIR/seeds $OUT/
