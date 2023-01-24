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
"""Integration code for centipede fuzzer."""

import subprocess
import os

from fuzzers import utils


def build():
    """Build benchmark."""
    san_cflags = ['-fsanitize-coverage=trace-loads']

    link_cflags = [
        '-Wno-unused-command-line-argument',
        '-Wl,-ldl,-lrt,-lpthread,/lib/weak.o'
    ]

    # TODO(Dongge): Build targets with sanitizers.
    with open('/src/centipede/clang-flags.txt', 'r',
              encoding='utf-8') as clang_flags_handle:
        centipede_cflags = [
            line.strip() for line in clang_flags_handle.readlines()
        ]

    cflags = san_cflags + centipede_cflags + link_cflags
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)
    utils.append_flags('LDFLAGS', ['/lib/weak.o'])

    os.environ['CC'] = '/clang/bin/clang'
    os.environ['CXX'] = '/clang/bin/clang++'
    os.environ['FUZZER_LIB'] = (
        '/src/centipede/bazel-bin/libcentipede_runner.pic.a')
    utils.build_benchmark()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer. Wrapper that uses the defaults when calling run_fuzzer."""
    run_fuzzer(input_corpus, output_corpus, target_binary)


def run_fuzzer(input_corpus, output_corpus, target_binary, extra_flags=None):
    """Run fuzzer."""
    if extra_flags is None:
        extra_flags = []

    # Seperate out corpus and crash directories as sub-directories of
    # |output_corpus| to avoid conflicts when corpus directory is reloaded.
    work_dir = os.path.join(output_corpus, 'work-dir')
    work_dir_crash = os.path.join(work_dir, 'crashes')
    crashes_dir = os.path.join(output_corpus, 'crashes')
    output_corpus = os.path.join(output_corpus, 'corpus')
    os.makedirs(work_dir)
    os.symlink(crashes_dir, work_dir_crash)
    os.makedirs(crashes_dir)
    os.makedirs(output_corpus)

    flags = [
        f'--workdir={work_dir}',
        f'--corpus_dir={output_corpus},{input_corpus}',
        f'--binary={target_binary}',
        # Run in fork mode to allow ignoring ooms, timeouts, crashes and
        # continue fuzzing indefinitely.
        '--fork_server=1',
        '--exit_on_crash=0',
        '--timeout=1200',
        '--rss_limit_mb=0',
        '--address_space_limit_mb=0',
    ]
    flags += extra_flags
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        flags.append(f'--dictionary={dictionary_path}')

    command = ['/out/centipede'] + flags
    print('[run_fuzzer] Running command: ' + ' '.join(command))
    subprocess.check_call(command)
