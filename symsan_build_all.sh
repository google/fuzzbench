#!/bin/bash

# TARGETS=(bloaty_fuzz_target curl_curl_fuzzer_http freetype2-2017 harfbuzz-1.3.2 jsoncpp_jsoncpp_fuzzer lcms-2017-03-21 libjpeg-turbo-07-2017 libpcap_fuzz_both libpng-1.6.38 libxml2-v2.9.2 libxslt_xpath mbedtls_fuzz_dtlsclient openssl_x509 openthread-2019-12-23 php_php-fuzz-parser proj4-2017-08-14 re2-2014-12-09 sqlite3_ossfuzz vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress)
TARGETS=(libpng-1.6.38 libxml2-v2.9.2)


MAKEFILETARGETS=()

for fuzzer in ${FUZZERS[@]}
do
    for target in ${TARGETS[@]}
    do
        MAKEFILETARGETS+=(build-$fuzzer-$target build-coverage-$fuzzer-$target)
    done
done

RESULTS=""
for f in ${MAKEFILETARGETS[@]}
do
    echo $f
    make $f
    RESULTS="$RESULTS $f=$? "
done
echo $RESULTS


