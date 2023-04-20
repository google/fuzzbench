# Copyright 2020 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

#!/bin/bash

ZLIB_DIR=$1
ZLIB_OUT_DIR=$2

export ZLIB_OUT_DIR="$ZLIB_OUT_DIR"
export ZLIB_DIR="$ZLIB_DIR"
mkdir -p "$ZLIB_OUT_DIR"

pushd "$ZLIB_DIR"
prefix="$ZLIB_OUT_DIR" ./configure --static
make -j$(nproc)
make install

OUT="$ZLIB_OUT_DIR"

echo 'export ZLIBLIB=$ZLIB_OUT_DIR/lib/' >> "$OUT/zlib_env.sh"
echo 'export ZLIBINC=$ZLIB_OUT_DIR/include/' >> "$OUT/zlib_env.sh"
echo 'export CFLAGS="-I$ZLIBINC $CPPFLAGS"' >> "$OUT/zlib_env.sh"
echo 'export CPPFLAGS="-I$ZLIBINC $CPPFLAGS"' >> "$OUT/zlib_env.sh"
echo 'export CXXFLAGS="-I$ZLIBINC $CPPFLAGS"' >> "$OUT/zlib_env.sh"
echo 'export LDFLAGS="-L$ZLIBLIB $LDFLAGS"' >> "$OUT/zlib_env.sh"
echo 'export LD_LIBRARY_PATH="$ZLIBLIB:$LD_LIBRARY_PATH" ' >> "$OUT/zlib_env.sh"

popd