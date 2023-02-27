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


# Do this here because the original python3.8 gets clobbered.
apt-get update && apt-get install python3 python3-pip -y

# This library can end up being linked to the fuzzer but it is not in the
# runner Dockerfile.
apt-get remove -y libfreetype6

python3.8 -m pip install ninja meson==0.56.0

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
ninja -v -j$(nproc) -C $build test/fuzzing/hb-shape-fuzzer
mv $build/test/fuzzing/hb-shape-fuzzer $OUT/

# Archive and copy to $OUT seed corpus if the build succeeded.
mkdir all-fonts
for d in \
    test/shape/data/in-house/fonts \
    test/shape/data/aots/fonts \
    test/shape/data/text-rendering-tests/fonts \
    test/api/fonts \
    test/fuzzing/fonts \
    perf/fonts \
    ; do
    cp $d/* all-fonts/
done

mkdir $OUT/seeds
cp all-fonts/* $OUT/seeds/
