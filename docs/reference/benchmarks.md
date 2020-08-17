---
layout: default
title: Benchmarks
nav_order: 5
permalink: /reference/benchmarks/
parent: Reference
---

# Benchmarks

This page describes each benchmark that is part of fuzzbench.

The table below was generated using benchmarks.py.

| Benchmark                   | Fuzz target            | Has dictionary? | Seed type\*              | Number of seed inputs  | Number of progam edges\*\*| Binary Size (MB)\*\*\*|
|:---------------------------:|:----------------------:|:---------------:|:------------------------:|:----------------------:|:------------ ------------:|:----------------------:
| bloaty_fuzz_target          | fuzz_target            | False           | ELF, Mach-O, WebAssembly | 94                     | 89530                     | 43.74                 |
| curl_curl_fuzzer_http       | curl_fuzzer_http       | False           | HTTP response            | 31                     | 62523                     | 20.11                 |
| freetype2-2017              | fuzz-target            | False           | TTF, OTF, WOFF           | 2                      | 19056                     | 6.76                  |
| harfbuzz-1.3.2              | fuzz-target            | False           | TTF, OTF, TTC            | 58                     | 10021                     | 6.24                  |
| jsoncpp_jsoncpp_fuzzer      | jsoncpp_fuzzer         | True            | JSON                     | 0                      | 5536                      | 5.96                  |
| lcms-2017-03-21             | fuzz-target            | True            | ICC profile              | 1                      | 6959                      | 6.11                  |
| libjpeg-turbo-07-2017       | fuzz-target            | False           | JPEG                     | 1                      | 9586                      | 6.4                   |
| libpcap_fuzz_both           | fuzz_both              | False           | PCAP                     | 0                      | 8149                      | 6.14                  |
| libpng-1.2.56               | fuzz-target            | True            | PNG                      | 1                      | 2991                      | 5.8                   |
| libxml2-v2.9.2              | fuzz-target            | True            | XML                      | 0                      | 50461                     | 8.23                  |
| mbedtls_fuzz_dtlsclient     | fuzz_dtlsclient        | False           | custom                   | 1                      | 10942                     | 6.67                  |
| openssl_x509                | x509                   | True            | DER certificate          | 2241                   | 45989                     | 18.14                 |
| openthread-2019-12-23       | fuzz-target            | False           | custom                   | 0                      | 17932                     | 6.72                  |
| php_php-fuzz-parser         | php-fuzz-parser        | True            | PHP                      | 2782                   | 123767                    | 15.57                 |
| proj4-2017-08-14            | fuzz-target            | True            | custom                   | 44                     | 6156                      | 6.17                  |
| re2-2014-12-09              | fuzz-target            | True            | custom                   | 0                      | 6547                      | 6.02                  |
| sqlite3_ossfuzz             | ossfuzz                | True            | custom                   | 1258                   | 45136                     | 7.9                   |
| systemd_fuzz-link-parser    | fuzz-link-parser       | False           | custom                   | 6                      | 53453                     | 5.91                  |
| vorbis-2017-12-11           | fuzz-target            | False           | OGG                      | 1                      | 5022                      | 6.0                   |
| woff2-2016-05-06            | fuzz-target            | False           | WOFF                     | 62                     | 10923                     | 6.72                  |
| zlib_zlib_uncompress_fuzzer | zlib_uncompress_fuzzer | False           | Zlib compressed          | 0                      | 875                       | 5.69                  |

\* "custom" means that it has a special encoding in the data format that does
not allow for aquiring seeds by normal means.
\*\*Number of program edges is the number of
["guards"](https://clang.llvm.org/docs/SanitizerCoverage.html#id2) in the
libFuzzer build of the target.
\*\*\*Size is determined by the size of the libFuzzer build of the target.
