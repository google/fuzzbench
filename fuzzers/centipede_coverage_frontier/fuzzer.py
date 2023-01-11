# Copyright 2022 Google LLC
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
"""Integration code for a mode of centipede fuzzer."""
from fuzzers.centipede import fuzzer
from fuzzers import utils
import os

def build():
    """Build benchmark."""
#    fuzzer.build()
    san_cflags = ['-fsanitize-coverage=trace-pc-guard,pc-table,control-flow']

    link_cflags = [
                '-Wno-error=unused-command-line-argument',
                '-ldl',
                '-lrt',
                '-lpthread',
                '/lib/weak.o',
                ]
    centipede_flags = [
        '-DFUZZING_BUILD_MODE_UNSAFE_FOR_PRODUCTION',
        '-fno-builtin',
        '-O2',
        '-gline-tables-only']
    cflags = san_cflags + link_cflags + centipede_flags
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)
    os.environ['CC'] = '/usr/local/bin/clang'
    os.environ['CXX'] = '/usr/local/bin/clang++'
    os.environ['FUZZER_LIB'] = (
                '/src/centipede/bazel-bin/libcentipede_runner.pic.a')
    utils.build_benchmark()

def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer. Wrapper that uses the defaults when calling run_fuzzer."""
    # Use coverage frontier when choosing the corpus element to mutate.
    mode_flags = ['--use_coverage_frontier=1']
    fuzzer.run_fuzzer(input_corpus,
                      output_corpus,
                      target_binary,
                      extra_flags=mode_flags)
