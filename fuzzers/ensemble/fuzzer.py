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
"""Integration code for AFL fuzzer."""

import collections
import glob
import shutil
import subprocess
import os
import tempfile

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer
# OUT environment variable is the location of build directory (default is /out).

# Fuzz each fuzzer for 2 hour before rotating.
SECONDS_PER_FUZZER = 60 * 60 * 2 

# List of fuzzers used for ensemble fuzzing.
FUZZER_LIST = ['aflfast', 'fairfuzz', 'mopt', 'aflplusplus', 'aflsmart']


def prepare_build_environment():
    """Set environment variables used to build AFL-based fuzzers."""
    utils.set_no_sanitizer_compilation_flags()

    cflags = ['-O3', '-fsanitize-coverage=trace-pc-guard']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'
    os.environ['FUZZER_LIB'] = '/libAFLDriver.a'


def build():
    """Build benchmark with AFL."""
    prepare_build_environment()

    utils.build_benchmark()

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    for fuzzer in FUZZER_LIST:
        shutil.copy(os.path.join('/' + fuzzer, 'afl-fuzz'),
                    os.path.join(os.environ['OUT'], fuzzer))

    # AFLSmart Setup
    # Copy Peach binaries to OUT
    shutil.copytree(
        '/aflsmart/peach-3.0.202-source/output/linux_x86_64_debug/bin',
        os.environ['OUT'] + '/peach-3.0.202')

    # Copy supported input models
    for file in glob.glob('/aflsmart/input_models/*.xml'):
        print(file)
        shutil.copy(file, os.environ['OUT'])


# pylint: disable=too-many-arguments
def run_afl_fuzz(fuzzer_name,
                 input_corpus,
                 output_corpus,
                 target_binary,
                 timeout,
                 additional_flags=None,
                 hide_output=False):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    # FIXME: Currently AFL will exit if it encounters a crashing input in seed
    # corpus (usually timeouts). Add a way to skip/delete such inputs and
    # re-run AFL. This currently happens with a seed in wpantund benchmark.
    print('[run_fuzzer] Running target with afl-fuzz')
    command = [
        os.path.join('.', fuzzer_name),
        '-i',
        input_corpus,
        '-o',
        output_corpus,
        # Use deterministic mode as it does best when we don't have
        # seeds which is often the case.
        '-d',
        # Use no memory limit as ASAN doesn't play nicely with one.
        '-m',
        'none'
    ]
    if additional_flags:
        command.extend(additional_flags)
    command += [
        '--',
        target_binary,
        # Pass INT_MAX to afl the maximize the number of persistent loops it
        # performs.
        '2147483647'
    ]
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.call(command,
                    stdout=output_stream,
                    stderr=output_stream,
                    timeout=timeout)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    os.environ['AFL_FAST_CAL'] = '1'
    os.environ['PATH'] += os.pathsep + '/out/peach-3.0.202/'
    fuzzer_queue = collections.deque(FUZZER_LIST, maxlen=5)

    tmp_dir = tempfile.TemporaryDirectory()
    next_fuzzer_input_corpus = os.path.join(str(tmp_dir), 'input_corpus')
    shutil.copytree(input_corpus, next_fuzzer_input_corpus)
    while True:
        fuzzer_name = fuzzer_queue[0]
        additional_flags = None
        if fuzzer_name == 'mopt':
            additional_flags = [
                # Enable Mopt mutator with pacemaker fuzzing mode at first. This
                # is also recommended in a short-time scale evaluation.
                '-L',
                '0',
            ]
        if fuzzer_name == 'aflsmart':
            input_model = ''
            benchmark_name = os.environ['BENCHMARK']
            if benchmark_name == 'libpng-1.2.56':
                input_model = 'png.xml'
            if benchmark_name == 'libpcap_fuzz_both':
                input_model = 'pcap.xml'
            if benchmark_name == 'libjpeg-turbo-07-2017':
                input_model = 'jpeg.xml'
            if input_model:
                additional_flags = [
                    # Enable stacked mutations
                    '-h',
                    # Enable structure-aware fuzzing
                    '-w',
                    'peach',
                    # Select input model
                    '-g',
                    input_model,
                ]
        try:
            fuzzer_output_dir = os.path.join(output_corpus, fuzzer_name)
            run_afl_fuzz(fuzzer_name,
                         next_fuzzer_input_corpus,
                         fuzzer_output_dir,
                         target_binary,
                         SECONDS_PER_FUZZER,
                         additional_flags=additional_flags)
        except subprocess.TimeoutExpired:
            tmp_dir.cleanup()
            fuzzer_queue.rotate(1)
            next_fuzzer_name = fuzzer_name
            print('Switching to fuzzer to {0}.'.format(next_fuzzer_name))
            tmp_dir = tempfile.TemporaryDirectory()
            next_fuzzer_input_corpus = os.path.join(str(tmp_dir),
                                                    'input_corpus')
            shutil.copytree(os.path.join(fuzzer_output_dir, 'queue'),
                            next_fuzzer_input_corpus)
