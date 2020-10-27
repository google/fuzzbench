#!/bin/bash -eu
# Copyright 2016 Google Inc.
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

# Disable:
# 1. UBSan vptr since target built with -fno-rtti.
export CFLAGS="$CFLAGS -fno-sanitize=vptr -DHB_NO_VISIBILITY"
export CXXFLAGS="$CXXFLAGS -fno-sanitize=vptr -DHB_NO_VISIBILITY"

# setup
build=$WORK/build

# cleanup
rm -rf $build
mkdir -p $build

# Build the library.
meson --default-library=static --wrap-mode=nodownload \
      -Dexperimental_api=true \
      -Dfuzzer_ldflags="$(echo $LIB_FUZZING_ENGINE)" \
      $build \
   || (cat build/meson-logs/meson-log.txt && false)

# Build the fuzzers.
ninja -v -j$(nproc) -C $build test/fuzzing/hb-subset-fuzzer
mv $build/test/fuzzing/hb-subset-fuzzer $OUT/

# Archive and copy to $OUT seed corpus if the build succeeded.
mkdir all-fonts
for d in \
	test/shaping/data/in-house/fonts \
	test/shaping/data/aots/fonts \
	test/shaping/data/text-rendering-tests/fonts \
	test/api/fonts \
	test/fuzzing/fonts \
	perf/fonts \
	; do
	cp $d/* all-fonts/
done
zip $OUT/hb-subset-fuzzer_seed_corpus.zip all-fonts/*
