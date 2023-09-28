#!/bin/bash -eu
# Copyright 2023 Google LLC
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

# build dependencies statically
if [ "$SANITIZER" = "memory" ]
then
    (
    cd zlib
    ./configure --static
    make -j$(nproc) clean
    make -j$(nproc) all
    make -j$(nproc) install
    )
    # Temporary workaround for https://github.com/rust-lang/rust/issues/107149
    # until oss-fuzz clang is up to rustc clang (15.0.6).
    export RUSTFLAGS="$RUSTFLAGS -Zsanitizer-memory-track-origins -Cllvm-args=-msan-eager-checks=0"
fi

(
tar -xvzf pcre2-10.39.tar.gz
cd pcre2-10.39
./configure --disable-shared
make -j$(nproc) clean
make -j$(nproc) all
make -j$(nproc) install
)

tar -xvzf lz4-1.9.2.tar.gz
cd lz4-1.9.2
make liblz4.a
cp lib/liblz4.a /usr/local/lib/
cp lib/lz4*.h /usr/local/include/
cd ..

tar -xvzf jansson-2.12.tar.gz
cd jansson-2.12
./configure --disable-shared
make -j$(nproc)
make install
cd ..

tar -xvzf libpcap-1.9.1.tar.gz
cd libpcap-1.9.1
./configure --disable-shared
make -j$(nproc)
make install
cd ..

cd fuzzpcap
mkdir build
cd build
cmake ..
make install
cd ../..

cd libyaml
./bootstrap
./configure --disable-shared
make -j$(nproc)
make install
cd ..

export CARGO_BUILD_TARGET="x86_64-unknown-linux-gnu"
# cf https://github.com/google/sanitizers/issues/1389
export MSAN_OPTIONS=strict_memcmp=false

#run configure with right options
if [ "$SANITIZER" = "address" ]
then
    export RUSTFLAGS="$RUSTFLAGS -Cpasses=sancov-module -Cllvm-args=-sanitizer-coverage-level=4 -Cllvm-args=-sanitizer-coverage-trace-compares -Cllvm-args=-sanitizer-coverage-inline-8bit-counters -Cllvm-args=-sanitizer-coverage-pc-table -Clink-dead-code -Cllvm-args=-sanitizer-coverage-stack-depth -Ccodegen-units=1"
    export RUSTFLAGS="$RUSTFLAGS -Cdebug-assertions=yes"
fi

#we did not put libhtp there before so that cifuzz does not remove it
cp -r libhtp suricata/
# build project

cd suricata
sh autogen.sh

./src/tests/fuzz/oss-fuzz-configure.sh
make -j$(nproc)

(
cd src
ls fuzz_* | while read i; do cp $i $OUT/$i; done
)
