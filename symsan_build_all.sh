#!/bin/bash

TARGETS=(libpng-1.6.38 libxml2-v2.9.2)
TARGETS=(bloaty_fuzz_target curl_curl_fuzzer_http freetype2-2017 harfbuzz-1.3.2 jsoncpp_jsoncpp_fuzzer lcms-2017-03-21 libjpeg-turbo-07-2017 libpcap_fuzz_both libpng-1.6.38 libxml2-v2.9.2 libxslt_xpath mbedtls_fuzz_dtlsclient openssl_x509 openthread-2019-12-23 php_php-fuzz-parser proj4-2017-08-14 re2-2014-12-09 sqlite3_ossfuzz vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer)

FUZZERS=(symsan)



MAKEFILETARGETS=()

for fuzzer in ${FUZZERS[@]}
do
    for target in ${TARGETS[@]}
    do
        MAKEFILETARGETS+=(build-$fuzzer-$target)
    done
done

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


