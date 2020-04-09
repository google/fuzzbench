#!/bin/bash -ex

. $(dirname $0)/../common.sh

get_git_tag https://github.com/mpruett/audiofile.git  audiofile-0.3.6 SRC


build_lib() {
  rm -rf BUILD
  cp -rf SRC BUILD
  # . use -fpermissive to avoid compilation error in left shift of negative
  # . use -C libaudiofile to avoid building the utils that are not needed
  (cd BUILD && ./autogen.sh &&
   CXXFLAGS="$CXXFLAGS -fpermissive" ./configure --disable-docs   \
     --disable-examples --enable-static --disable-shared &&
   make -C libaudiofile)
}

build_lib

$CXX $CXXFLAGS -std=c++11 -IBUILD -IBUILD/libaudiofile audiofile_sfconvert_fuzz.cc BUILD/libaudiofile/.libs/libaudiofile.a ./BUILD/libaudiofile/modules/.libs/libmodules.a ./BUILD/libaudiofile/alac/.libs/libalac.a  $FUZZER_LIB -o $FUZZ_TARGET
