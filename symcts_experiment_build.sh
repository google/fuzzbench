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
FUZZERS=(symcc_aflplusplus symsan honggfuzz libfuzzer symcts symcts_afl symcts_symqemu_afl aflplusplus)
TARGETS=(curl_curl_fuzzer_http harfbuzz-1.3.2 jsoncpp_jsoncpp_fuzzer libpng-1.6.38 libxml2-v2.9.2 libxslt_xpath mbedtls_fuzz_dtlsclient openssl_x509 php_php-fuzz-parser re2-2014-12-09 vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer)

FUZZERS=(symcc_aflplusplus symsan afl_companion symcts_afl symcts_afl_weak symcts_symqemu_afl symcts_symqemu_afl_weak)
TARGETS=(stb_stbi_read_fuzzer libpng-1.6.38 curl_curl_fuzzer_http)

# openthread-2019-12-23 - honggfuzz doesn't build due to strlcpy not defined??
# sqlite3_ossfuzz - mksourceid


MAKEFILETARGETS=()

for target in ${TARGETS[@]}
do
    MAKEFILETARGETS+=(build-coverage-$target)
    for fuzzer in ${FUZZERS[@]}
    do
        MAKEFILETARGETS+=(build-$fuzzer-$target)
    done
done

echo ${MAKEFILETARGETS[@]}
make ${MAKEFILETARGETS[@]} -j4 -k
