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
#
"""Integration code for Zafl fuzzer-prep binary rewriter."""

import os

from fuzzers import utils
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


#
# how to build a fuzzbench benchmark
#
def build():
    """Build benchmark."""
    os.environ['AFL_MAP_SIZE'] = '65536'
    os.environ['AFL_LLVM_MAP_ADDR'] = '0x1000000'
    os.environ['ZAFL_FIXED_MAP_ADDR'] = '0x1000000'
    os.environ['CC'] = '/cc.sh'
    os.environ['CXX'] = '/cxx.sh'
    if 'LD_LIBRARY_PATH' in os.environ:
        os.environ['LD_LIBRARY_PATH'] = os.environ['LD_LIBRARY_PATH'] + ':/out'
    else:
        os.environ['LD_LIBRARY_PATH'] = '/out'

    utils.append_flags('CFLAGS', ['-fPIC', '-lpthread'])
    utils.append_flags('CXXFLAGS', ['-fPIC', '-lpthread'])
    os.environ['FUZZER_LIB'] = '/out/fakeLibrary.a'
    utils.build_benchmark()
    res = os.system('bash -x /zafl_bins.sh')
    if res != 0:
        os.system('rm -rf /out')


#
# how to fuzz a fuzzbench benchmark
#
def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    run_options = []
    os.environ['AFL_MAP_SIZE'] = '65536'
    os.environ['AFL_LLVM_MAP_ADDR'] = '0x1000000'
    os.environ['ZAFL_DRIVER_SETS_UP_MAP'] = '1'
    print(os.environ)
    aflplusplus_fuzzer.fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            flags=(run_options))
