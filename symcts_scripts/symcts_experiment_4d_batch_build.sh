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

BATCH_NUM=$1

FUZZERS=(aflplusplus symcts symcts_symqemu symcts_symqemu_afl symcts_afl symsan symcc_aflplusplus)

case $BATCH_NUM in
    1)
        TARGETS=(bloaty_fuzz_target zlib_zlib_uncompress_fuzzer )
        EXPERIMENT_NAME="4d1-bloaty-zlib-$(date +%Y%m%d-%H%M%S)"
        ;;
    2)
        TARGETS=(curl_curl_fuzzer_http freetype2_ftfuzzer)
        EXPERIMENT_NAME="4d2-curl-ft-$(date +%Y%m%d-%H%M%S)"
        ;;
    3)
        TARGETS=(harfbuzz_hb-shape-fuzzer jsoncpp_jsoncpp_fuzzer)
        EXPERIMENT_NAME="4d3-hb-js-$(date +%Y%m%d-%H%M%S)"
        ;;
    4)
        TARGETS=(lcms_cms_transform_fuzzer libjpeg-turbo_libjpeg_turbo_fuzzer)
        EXPERIMENT_NAME="4d4-lcms-ljpg-$(date +%Y%m%d-%H%M%S)"
        ;;
    5)
        TARGETS=(libpcap_fuzz_both libpng_libpng_read_fuzzer)
        EXPERIMENT_NAME="4d5-lpcp-lpng-$(date +%Y%m%d-%H%M%S)"
        ;;
    6)
        TARGETS=(libxml2_xml libxslt_xpath)
        EXPERIMENT_NAME="4d6-lxml-xslt-$(date +%Y%m%d-%H%M%S)"
        ;;
    7)
        TARGETS=( openssl_x509)
        EXPERIMENT_NAME="4d7-oh264-ssl-$(date +%Y%m%d-%H%M%S)"
        ;;
    8)
        TARGETS=(openthread_ot-ip6-send-fuzzer proj4_proj_crs_to_crs_fuzzer)
        EXPERIMENT_NAME="4d8-ot-prj4-$(date +%Y%m%d-%H%M%S)"
        ;;
    9)
        TARGETS=(re2_fuzzer sqlite3_ossfuzz)
        EXPERIMENT_NAME="4d9-re2-sqlt-$(date +%Y%m%d-%H%M%S)"
        ;;
    10)
        TARGETS=(stb_stbi_read_fuzzer systemd_fuzz-link-parser)
        EXPERIMENT_NAME="4d10-stb-sysd-$(date +%Y%m%d-%H%M%S)"
        ;;
    11)
        TARGETS=(vorbis_decode_fuzzer woff2_convert_woff2ttf_fuzzer)
        EXPERIMENT_NAME="4d11-vrbs-woff-$(date +%Y%m%d-%H%M%S)"
        ;;
    *)
        echo "Invalid batch number"
        exit 1
        ;;
esac

# TARGETS=(
#     bloaty_fuzz_target
#     curl_curl_fuzzer_http
#     freetype2_ftfuzzer
#     harfbuzz_hb-shape-fuzzer
#     jsoncpp_jsoncpp_fuzzer
#     lcms_cms_transform_fuzzer
#     libjpeg-turbo_libjpeg_turbo_fuzzer
#     libpcap_fuzz_both
#     libpng_libpng_read_fuzzer
#     libxml2_xml
#     libxslt_xpath
#     openh264_decoder_fuzzer
#     openssl_x509
#     openthread_ot-ip6-send-fuzzer
#     proj4_proj_crs_to_crs_fuzzer
#     re2_fuzzer
#     sqlite3_ossfuzz
#     stb_stbi_read_fuzzer
#     systemd_fuzz-link-parser
#     vorbis_decode_fuzzer
#     woff2_convert_woff2ttf_fuzzer
#     zlib_zlib_uncompress_fuzzer
# )

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

set -x
# REMOVE build-symcc_aflplusplus-sqlite3_ossfuzz from the MAKEFILETARGETS
MAKEFILETARGETS=(${MAKEFILETARGETS[@]/build-symcc_aflplusplus-sqlite3_ossfuzz/})

echo ${MAKEFILETARGETS[@]}
make ${MAKEFILETARGETS[@]} -j4 -k
