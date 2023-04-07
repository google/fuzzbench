#!/bin/bash
FUZZERS=(symcc_aflplusplus symsan honggfuzz libfuzzer symcts symcts_afl symcts_symqemu_afl aflplusplus)
TARGETS=(curl_curl_fuzzer_http harfbuzz-1.3.2 jsoncpp_jsoncpp_fuzzer libpng-1.6.38 libxml2-v2.9.2 libxslt_xpath mbedtls_fuzz_dtlsclient openssl_x509 php_php-fuzz-parser re2-2014-12-09 vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer)

FUZZERS=(symcc_aflplusplus symsan symcts_afl aflplusplus)
TARGETS=(re2-2014-12-09 libpng-1.6.38 vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer)

# openthread-2019-12-23 - honggfuzz doesn't build due to strlcpy not defined??
# sqlite3_ossfuzz - mksourceid


MAKEFILETARGETS=()

for target in ${TARGETS[@]}
do
    for fuzzer in ${FUZZERS[@]}
    do
        MAKEFILETARGETS+=(build-$fuzzer-$target build-coverage-$target)
    done
done

echo ${MAKEFILETARGETS[@]}
make ${MAKEFILETARGETS[@]} -j -k
