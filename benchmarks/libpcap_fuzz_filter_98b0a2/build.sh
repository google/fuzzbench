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

cd libpcap
# build project
mkdir build
cd build
cmake -DDISABLE_DBUS=1 ..
make

# build fuzz targets
$CC $CFLAGS -I.. -c ../testprogs/fuzz/fuzz_filter.c -o fuzz_filter.o
$CXX $CXXFLAGS fuzz_filter.o -o $OUT/fuzz_filter libpcap.a $LIB_FUZZING_ENGINE

# export other associated stuff
cd ..
cp testprogs/fuzz/fuzz_*.options $OUT/
# builds corpus
cd $SRC/tcpdump/
zip -r fuzz_pcap_seed_corpus.zip tests/
cp fuzz_pcap_seed_corpus.zip $OUT/
cd $SRC/libpcap/testprogs/BPF
mkdir corpus
ls *.txt | while read i; do tail -1 $i > corpus/$i; done
zip -r fuzz_filter_seed_corpus.zip corpus/
cp fuzz_filter_seed_corpus.zip $OUT/
