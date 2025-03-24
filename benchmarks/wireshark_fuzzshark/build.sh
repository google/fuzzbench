#!/bin/bash -eu
# Copyright 2017 Google Inc.
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
#
################################################################################

WIRESHARK_BUILD_PATH="$WORK/build"
mkdir -p "$WIRESHARK_BUILD_PATH"

# Prepare Samples directory
export SAMPLES_DIR="$WORK/samples"
mkdir -p "$SAMPLES_DIR"
cp -a $SRC/wireshark-fuzzdb/samples/* "$SAMPLES_DIR"

# Make sure we build fuzzshark.
CMAKE_DEFINES="-DBUILD_fuzzshark=ON"

# compile static version of libs
# XXX, with static wireshark linking each fuzzer binary is ~346 MB (just libwireshark.a is 761 MB).
# XXX, wireshark is not ready for including static plugins into binaries.
CMAKE_DEFINES="$CMAKE_DEFINES -DENABLE_STATIC=ON -DENABLE_PLUGINS=OFF"

# disable optional dependencies
CMAKE_DEFINES="$CMAKE_DEFINES -DENABLE_PCAP=OFF -DENABLE_GNUTLS=OFF"

# There is no need to manually disable programs via BUILD_xxx=OFF since the
# all-fuzzers targets builds the minimum required binaries. However we do have
# to disable the Qt GUI and sharkd or else the cmake step will fail.
CMAKE_DEFINES="$CMAKE_DEFINES -DBUILD_wireshark=OFF -DBUILD_logray=OFF -DBUILD_sharkd=OFF"

cd "$WIRESHARK_BUILD_PATH"

cmake -G Ninja \
    -DENABLE_STATIC=ON \
    -DOSS_FUZZ=ON \
    -DINSTRUMENT_DISSECTORS_ONLY=ON \
    -DBUILD_fuzzshark=ON \
    -DBUILD_wireshark=OFF \
    -DBUILD_sharkd=OFF \
    -DENABLE_PCAP=OFF \
    -DENABLE_ZLIB=OFF \
    -DENABLE_MINIZIP=OFF \
    -DENABLE_LZ4=OFF \
    -DENABLE_BROTLI=OFF \
    -DENABLE_SNAPPY=OFF \
    -DENABLE_ZSTD=OFF \
    -DENABLE_NGHTTP2=OFF \
    -DENABLE_NGHTTP3=OFF \
    -DENABLE_LUA=OFF \
    -DENABLE_SMI=OFF \
    -DENABLE_GNUTLS=OFF \
    -DENABLE_NETLINK=OFF \
    -DENABLE_KERBEROS=OFF \
    -DENABLE_SBC=OFF \
    -DENABLE_SPANDSP=OFF \
    -DENABLE_BCG729=OFF \
    -DENABLE_AMRNB=OFF \
    -DENABLE_ILBC=OFF \
    -DENABLE_LIBXML2=OFF \
    -DENABLE_OPUS=OFF \
    -DENABLE_SINSP=OFF $SRC/wireshark/

# cmake -GNinja \
#       -DCMAKE_C_COMPILER=$CC -DCMAKE_CXX_COMPILER=$CXX \
#       -DCMAKE_C_FLAGS="-Wno-error=fortify-source -Wno-error=missing-field-initializers $CFLAGS" -DCMAKE_CXX_FLAGS="-Wno-error=fortify-source -Wno-error=missing-field-initializers $CXXFLAGS" \
#       -DDISABLE_WERROR=ON -DOSS_FUZZ=ON $CMAKE_DEFINES $SRC/wireshark/

ninja fuzzshark


$SRC/wireshark/tools/oss-fuzzshark/build.sh all
