#!/bin/bash -eu
# Copyright 2018 Google Inc.
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


mkdir seeds
find . -name "*.pcap" -exec cp {} seeds \;
cp -r seeds $OUT/

mkdir build 
cd build

cmake -G Ninja .. \
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
    -DENABLE_SINSP=OFF

ninja fuzzshark
cp run/fuzzshark $OUT/fuzzshark
export FUZZSHARK_TARGET="tcp"

