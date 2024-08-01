#!/bin/bash

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

TARGETS=(
    bloaty_fuzz_target
    curl_curl_fuzzer_http
    freetype2_ftfuzzer
    harfbuzz_hb-shape-fuzzer
    jsoncpp_jsoncpp_fuzzer
    lcms_cms_transform_fuzzer
    libjpeg-turbo_libjpeg_turbo_fuzzer
    libpcap_fuzz_both
    libpng_libpng_read_fuzzer
    libxml2_xml
    libxslt_xpath
    mbedtls_fuzz_dtlsclient
    openh264_decoder_fuzzer
    openssl_x509
    openthread_ot-ip6-send-fuzzer
    proj4_proj_crs_to_crs_fuzzer
    re2_fuzzer
    sqlite3_ossfuzz
    stb_stbi_read_fuzzer
    systemd_fuzz-link-parser
    vorbis_decode_fuzzer
    woff2_convert_woff2ttf_fuzzer
    zlib_zlib_uncompress_fuzzer
)

FUZZERS=(symsan symcts_afl)



MAKEFILETARGETS=()

for fuzzer in ${FUZZERS[@]}
do
    for target in ${TARGETS[@]}
    do
        MAKEFILETARGETS+=(build-$fuzzer-$target)
    done
done

make ${MAKEFILETARGETS[@]} -j4 -k

RESULTS=""
for f in ${MAKEFILETARGETS[@]}
do
    echo $f
    target_name=$(echo $f | sed s'/build-symsan-//')
    make $f 2>/dev/null
    RESULTS="$RESULTS    $target_name = $? "
    echo '$$$$$$$$$$$$$$$$$$$$$$$$$$'
    echo '$$$$$$$$$$$$$$$$$$$$$$$$$$'
    echo '$$$$$$$$$$$$$$$$$$$$$$$$$$'
    echo "$RESULTS"
    echo '$$$$$$$$$$$$$$$$$$$$$$$$$$'
    echo '$$$$$$$$$$$$$$$$$$$$$$$$$$'
    echo '$$$$$$$$$$$$$$$$$$$$$$$$$$'
done
echo $RESULTS


