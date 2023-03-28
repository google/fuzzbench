#!/bin/bash
FUZZERS=(symcts symcts_afl symcts_symqemu symcts_symqemu_afl honggfuzz libfuzzer symcc_aflplusplus symsan)
TARGETS=(curl_curl_fuzzer_http harfbuzz-1.3.2 jsoncpp_jsoncpp_fuzzer libpng-1.6.38 libxml2-v2.9.2 libxslt_xpath mbedtls_fuzz_dtlsclient openssl_x509 openthread-2019-12-23 php_php-fuzz-parser re2-2014-12-09 sqlite3_ossfuzz vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer)

MAKEFILETARGETS=()

for fuzzer in ${FUZZERS[@]}
do
    for target in ${TARGETS[@]}
    do
        MAKEFILETARGETS+=(build-$fuzzer-$target build-coverage-$target)
    done
done

echo ${MAKEFILETARGETS[@]}
make ${MAKEFILETARGETS[@]} -j 4
