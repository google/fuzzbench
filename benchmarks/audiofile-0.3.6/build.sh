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

get_git_tag https://github.com/mpruett/audiofile.git  audiofile-0.3.6 SRC

# XXX roachspray: funny, no sig for this version :/
wget ftp://ftp.gnu.org/gnu/libtool/libtool-1.4.2.tar.gz || (printf "wget failed" && exit 1)
tar zxvf libtool-1.4.2.tar.gz || (printf "unzip failed" && exit 1)
(cd libtool-1.4.2 && mkdir install && ./configure --prefix=`pwd`/install &&
 make && make install)

build_lib() {
  rm -rf BUILD
  cp -rf SRC BUILD
  # . use -fpermissive to avoid compilation error in left shift of negative
  # . use -C libaudiofile to avoid building the utils that are not needed
  # . not all crashes happen in 64-bit mode. Building default to 32-bit and
  #    must set CFLAGS b/c it's part C++ and part C.
  #
  (cd BUILD && PATH=`pwd`/../libtool-1.4.2/install/bin:$PATH ./autogen.sh &&
   CXXFLAGS="$CXXFLAGS -fpermissive -m32 -march=i686"   \
     CFLAGS="$CFLAGS -m32 -march=i686" ./configure      \
     --disable-docs --disable-examples --enable-static --disable-shared  && 
   make -C libaudiofile)
}

build_lib

#
# To test with the main() in audiofile_sfconvert_fuzz.cc, use -D_HAVE_MAIN
# and disable any fuzzer in sanitizer flag.
#

$CXX $CXXFLAGS -std=c++11 -nopie -m32 -march=i686 -IBUILD -IBUILD/libaudiofile audiofile_sfconvert_fuzz.cc BUILD/libaudiofile/.libs/libaudiofile.a ./BUILD/libaudiofile/modules/.libs/libmodules.a ./BUILD/libaudiofile/alac/.libs/libalac.a  $FUZZER_LIB -o $FUZZ_TARGET
