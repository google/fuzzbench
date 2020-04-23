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
  # we build and install bc was having issues with autogen.sh of dbus
  # makes building the rest easier too..
  (cd BUILD/libexpat/expat && ./buildconf.sh && ./configure && make &&
   make install)
  (cd BUILD/libdbus && 
    CFLAGS="${CFLAGS} -Wno-error" ./autogen.sh --disable-xml-docs --disable-doxygen-docs --disable-ducktype-docs &&
    make && make install)
  (cd BUILD/libpcap && ./configure && make &&
   cd ../tcpdump && ./configure && make)
}

#
# tcpdump really wants libpcap to share the same parent directory.
# 
mkdir SRC
git clone https://github.com/libexpat/libexpat.git SRC/libexpat
get_git_tag https://gitlab.freedesktop.org/dbus/dbus.git  dbus-1.10 SRC/libdbus
get_git_tag https://github.com/the-tcpdump-group/libpcap.git  libpcap-1.9.0 SRC/libpcap
get_git_tag https://github.com/the-tcpdump-group/tcpdump.git  tcpdump-4.9.0 SRC/tcpdump

build_lib

# copy over shared lib deps to /out
cp BUILD/libexpat/expat/lib/.libs/libexpat.so.1.6.11 $OUT/
ln -s $OUT/libexpat.so.1.6.11 $OUT/libexpat.so.1
ln -s $OUT/libexpat.so.1.6.11 $OUT/libexpat.so
cp BUILD/libdbus/dbus/.libs/libdbus-1.so.3.14.16 $OUT/
ln -s $OUT/libdbus-1.so.3.14.16 $OUT/libdbus-1.so.3
ln -s $OUT/libdbus-1.so.3.14.16 $OUT/libdbus-1.so

#
# To test with the main() in tcpdump_fuzz.cc, use -D_HAS_MAIN and disable any
# fuzzer in sanitizer flag / use of FUZZER_LIB.
#
$CXX $CXXFLAGS -std=c++11 -Wl,-rpath,/out -IBUILD/libpcap -IBUILD/tcpdump  \
  ${SCRIPT_DIR}/tcpdump_fuzz.cc BUILD/libpcap/libpcap.a  \
  BUILD/tcpdump/libnetdissect.a  \
  -L$OUT -ldbus-1 -L$OUT -lexpat -lcrypto -lssl \
  $FUZZER_LIB -o $FUZZ_TARGET
cp -r $SCRIPT_DIR/seeds $OUT/
