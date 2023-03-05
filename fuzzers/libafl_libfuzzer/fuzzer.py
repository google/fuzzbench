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
"""Integration code for a LibAFL-based fuzzer."""

import os
import subprocess

from fuzzers import utils


def prepare_fuzz_environment():
    """Prepare to fuzz with a LibAFL-based fuzzer."""
    os.environ['ASAN_OPTIONS'] = 'abort_on_error=1:detect_leaks=0:' \
                                 'malloc_context_size=0:symbolize=0:' \
                                 'allocator_may_return_null=1:' \
                                 'detect_odr_violation=0:handle_segv=0:' \
                                 'handle_sigbus=0:handle_abort=0:' \
                                 'handle_sigfpe=0:handle_sigill=0'
    os.environ['UBSAN_OPTIONS'] = 'abort_on_error=1:' \
                                  'allocator_release_to_os_interval_ms=500:' \
                                  'handle_abort=0:handle_segv=0:' \
                                  'handle_sigbus=0:handle_sigfpe=0:' \
                                  'handle_sigill=0:print_stacktrace=0:' \
                                  'symbolize=0:symbolize_inline_frames=0'


def build():
    """Build benchmark."""
    # With LibFuzzer we use -fsanitize=fuzzer-no-link for build CFLAGS and then
    # /usr/lib/libFuzzer.a as the FUZZER_LIB for the main fuzzing binary. This
    # allows us to link against a version of LibFuzzer that we specify.
    cflags = ['-fsanitize=fuzzer-no-link']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    os.environ['CC'] = 'clang'
    os.environ['CXX'] = 'clang++'

    # merge all of our lib into a single .o, then pack that into a static lib
    subprocess.check_call([
        '/usr/bin/ld', '-Ur', '--whole-archive', '/usr/lib/libFuzzer.a', '-o',
        '/tmp/libFuzzerMerged.o'
    ])
    subprocess.check_call(['/usr/bin/rm', '/usr/lib/libFuzzer.a'])
    subprocess.check_call(
        ['/usr/bin/ar', 'cr', '/usr/lib/libFuzzer.a', '/tmp/libFuzzerMerged.o'])

    os.environ['FUZZER_LIB'] = '/usr/lib/libFuzzer.a'

    utils.build_benchmark()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer. Wrapper that uses the defaults when calling
    run_fuzzer."""
    run_fuzzer(input_corpus, output_corpus, target_binary)


def run_fuzzer(input_corpus, output_corpus, target_binary, extra_flags=None):
    """Run fuzzer."""
    if extra_flags is None:
        extra_flags = []

    # ASAN doesn't play nicely with our signal handling
    # in the future, we will make this more compatible with libfuzzer, but
    # for the initial implementation, we consider this sufficient
    prepare_fuzz_environment()

    # Seperate out corpus and crash directories as sub-directories of
    # |output_corpus| to avoid conflicts when corpus directory is reloaded.
    crashes_dir = os.path.join(output_corpus, 'crashes')
    output_corpus = os.path.join(output_corpus, 'corpus')
    os.makedirs(crashes_dir)
    os.makedirs(output_corpus)

    flags = [
        # not supported by libafl_libfuzzer currently
        '-print_final_stats=1',
        # `close_fd_mask` to prevent too much logging output from the target.
        '-close_fd_mask=3',
        # Run in fork mode to allow ignoring ooms, timeouts, crashes and
        # continue fuzzing indefinitely.
        '-fork=1',
        '-ignore_ooms=1',
        '-ignore_timeouts=1',
        '-ignore_crashes=1',

        # Don't use LSAN's leak detection. Other fuzzers won't be using it and
        # using it will cause libFuzzer to find "crashes" no one cares about.
        # libafl_libfuzzer does not do leak checking regardless; not supported
        '-detect_leaks=0',

        # Store crashes along with corpus for bug based benchmarking.
        f'-artifact_prefix={crashes_dir}/',
    ]
    flags += extra_flags
    if 'ADDITIONAL_ARGS' in os.environ:
        flags += os.environ['ADDITIONAL_ARGS'].split(' ')
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        flags.append('-dict=' + dictionary_path)

    command = [target_binary] + flags + [output_corpus, input_corpus]
    print('[run_fuzzer] Running command: ' + ' '.join(command))
    subprocess.check_call(command)
