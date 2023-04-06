#!/bin/bash

FUZZERS=(symcc_aflplusplus symsan honggfuzz libfuzzer symcts symcts_afl symcts_symqemu_afl aflplusplus)
# TARGETS=(curl_curl_fuzzer_http harfbuzz-1.3.2 jsoncpp_jsoncpp_fuzzer libpng-1.6.38 libxml2-v2.9.2 libxslt_xpath mbedtls_fuzz_dtlsclient openssl_x509 php_php-fuzz-parser re2-2014-12-09 vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer)

# TARGETS=(openssl_x509 re2-2014-12-09 vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer)
TARGETS=(curl_curl_fuzzer_http harfbuzz-1.3.2 jsoncpp_jsoncpp_fuzzer libpng-1.6.38 libxml2-v2.9.2)

EXPERIMENT_NAME="symcts-$(date +%Y%m%d-%H%M%S)"

# --benchmarks libpng-1.2.56
# libpcap_fuzz_both vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer
    # --no-seeds \

PYTHONPATH=. python3.10 experiment/run_experiment.py \
    --allow-uncommitted-changes \
    --no-seeds \
    --no-dictionaries \
    --experiment-config symcts_experiment_config.yaml \
    --concurrent-builds 1 \
    --runners-cpus 80 \
    --measurers-cpus 16 \
    --experiment-name $EXPERIMENT_NAME \
    --fuzzers ${FUZZERS[@]} \
    --benchmarks ${TARGETS[@]} \
