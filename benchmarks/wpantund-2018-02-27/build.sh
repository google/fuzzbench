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
  if [[ -f $FUZZER_LIB ]]; then
    cp $FUZZER_LIB BUILD/src/wpantund/
    cp $FUZZER_LIB BUILD/src/ncp-spinel/
  fi
  (cd BUILD && ./bootstrap.sh && ./configure \
    --enable-fuzz-targets             \
    --disable-shared                  \
    --enable-static                   \
    CC="${CC}"                        \
    CXX="${CXX}"                      \
    FUZZ_LIBS="${FUZZER_LIB}" \
    FUZZ_CFLAGS="${CFLAGS}"           \
    FUZZ_CXXFLAGS="${CXXFLAGS}"       \
    LDFLAGS="-lpthread"               \
    && make -j $JOBS)
}

get_git_revision https://github.com/openthread/wpantund.git \
  7fea6d7a24a52f6a61545610acb0ab8a6fddf503 SRC
build_lib

if [[ ! -d $OUT/seeds ]]; then
  cp -r BUILD/etc/fuzz-corpus/wpantund-fuzz $OUT/seeds

  # Remove this seed as it times out with vanilla AFL and cannot be used for
  # fair fuzzer comparison.
  rm $OUT/seeds/config-corpus-seed-0001
fi

cp BUILD/src/wpantund/wpantund-fuzz $FUZZ_TARGET
