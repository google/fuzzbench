# Supported benchmarks

[AFLSmart](https://github.com/aflsmart/aflsmart) is a structure-aware greybox-fuzzer and it is designed to work best for programs taking chunk-based file formats (e.g., JPEG, PNG and many others) as inputs. To fully enable its structure-aware mode, AFLSmart requires input models (e.g., grammar). So if you evaluate AFLSmart on FuzzBench, please focus on the results for the following benchmarks. We keep trying to include more input models so that more benchmarks will be supported.

1. libpng-1.2.56

2. libjpeg-turbo-07-2017

3. libpcap_fuzz_both

4. freetype2-2017

5. vorbis-2017-12-11

6. bloaty_fuzz_target

Since the experiment summary diagram of the default FuzzBench report is automatically generated based on the results of all benchmarks, many of them have not been supported by AFLSmart, the ranking of AFLSmart in that diagram may not be correct.

