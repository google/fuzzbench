#!/bin/bash

FUZZERS=(symcc_aflplusplus symsan honggfuzz libfuzzer symcts symcts_afl symcts_symqemu_afl aflplusplus)
# TARGETS=(curl_curl_fuzzer_http harfbuzz-1.3.2 jsoncpp_jsoncpp_fuzzer libpng-1.6.38 libxml2-v2.9.2 libxslt_xpath mbedtls_fuzz_dtlsclient openssl_x509 php_php-fuzz-parser re2-2014-12-09 vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer)

# TARGETS=(openssl_x509 re2-2014-12-09 vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer)

FUZZERS=(symcc_aflplusplus symsan symcts_afl afl_companion)
TARGETS=(stb_stbi_read_fuzzer libpng-1.6.38 curl_curl_fuzzer_http)

EXPERIMENT_NAME="symcts-$(date +%Y%m%d-%H%M%S)"

# --benchmarks libpng-1.2.56
# libpcap_fuzz_both vorbis-2017-12-11 woff2-2016-05-06 zlib_zlib_uncompress_fuzzer
# --no-seeds \

# use python3.10 if it exists, otherwise use python3.8 if it exists, otherwise use python3
PYTHON3=$(which python3.10 || which python3.8 || which python3)

    # --no-seeds \
    # --no-dictionaries \

PYTHONPATH=. "$PYTHON3" experiment/run_experiment.py \
    --allow-uncommitted-changes \
    --experiment-config symcts_experiment_config.yaml \
    --concurrent-builds 1 \
    --runners-cpus 60 \
    --measurers-cpus 36 \
    --experiment-name $EXPERIMENT_NAME \
    --fuzzers ${FUZZERS[@]} \
    --benchmarks ${TARGETS[@]} \
