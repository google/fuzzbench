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
"""Integration code for AFLplusplus fuzzer."""

# This optimized afl++ variant should always be run together with
# "aflplusplus" to show the difference - a default configured afl++ vs.
# a hand-crafted optimized one. afl++ is configured not to enable the good
# stuff by default to be as close to vanilla afl as possible.
# But this means that the good stuff is hidden away in this benchmark
# otherwise.

import os
import shutil
import glob

from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


def build():  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    benchmark_name = os.environ['BENCHMARK']

    if benchmark_name == 'bloaty_fuzz_target':
        aflplusplus_fuzzer.build("tracepc", "cmplog", "dict2file")
    elif benchmark_name == 'curl_curl_fuzzer_http':
        aflplusplus_fuzzer.build("tracepc", "cmplog")
    elif benchmark_name == 'libjpeg-turbo-07-2017':
        aflplusplus_fuzzer.build("tracepc", "dict2file")
    elif benchmark_name == 'libpcap_fuzz_both':
        aflplusplus_fuzzer.build("tracepc", "dict2file")
    elif benchmark_name == 'libpng-1.2.56':
        aflplusplus_fuzzer.build("lto", "laf", "fixed")
    elif benchmark_name == 'libxml2-v2.9.2':
        aflplusplus_fuzzer.build("lto", "fixed")
    elif benchmark_name == 'mbedtls_fuzz_dtlsclient':
        aflplusplus_fuzzer.build("tracepc")
    elif benchmark_name == 'openssl_x509':
        aflplusplus_fuzzer.build("tracepc", "dict2file")
    elif benchmark_name == 'php_php-fuzz-parser':
        aflplusplus_fuzzer.build("classic", "ctx", "cmplog")
    elif benchmark_name == 'proj4-2017-08-14':
        aflplusplus_fuzzer.build("tracepc", "cmplog")
    elif benchmark_name == 'sqlite3_ossfuzz':
        aflplusplus_fuzzer.build("lto", "fixed", "cmplog")
    elif benchmark_name == 'systemd_fuzz-link-parser':
        aflplusplus_fuzzer.build("lto", "cmplog")
    elif benchmark_name == 'vorbis-2017-12-11':
        aflplusplus_fuzzer.build("tracepc", "laf")
    elif benchmark_name == 'woff2-2016-05-06':
        aflplusplus_fuzzer.build("tracepc", "dict2file")
    elif benchmark_name == 'zlib_zlib_uncompress_fuzzer':
        aflplusplus_fuzzer.build("tracepc", "cmplog")
    else:
        aflplusplus_fuzzer.build("lto", "cmplog", "fixed")

    for copy_file in glob.glob("/afl/libc*"):
        shutil.copy(copy_file, os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):  # pylint: disable=too-many-branches,too-many-statements
    """Run fuzzer."""
    benchmark_name = os.environ['BENCHMARK']

    if benchmark_name == 'bloaty_fuzz_target':
        run_options = ['-Z']
    if benchmark_name == 'lcms-2017-03-21':
        run_options = ['-Z']
    if benchmark_name == 'libpcap_fuzz_both':
        run_options = ['-Z']
    if benchmark_name == 'libxslt_xpath':
        run_options = ['-Z']
    if benchmark_name == 'openssl_x509':
        run_options = ['-Z']
    if benchmark_name == 'proj4-2017-08-14':
        run_options = ['-Z']
    else:
        run_options = []

    aflplusplus_fuzzer.fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            flags=(run_options))
