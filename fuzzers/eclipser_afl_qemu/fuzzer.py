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
"""Integration code for Eclipser fuzzer. Note that starting from v2.0, Eclipser
relies on AFL to perform random-based fuzzing."""

import subprocess
import os
import threading

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers.afl_qemu import fuzzer as afl_fuzzer_qemu


def get_eclipser_outdir(target_directory):
    """Return path to eclipser target directory."""
    return os.path.join(target_directory, 'eclipser_benchmark')


def build():
    """Build benchmark."""
    # Backup the environment.
    new_env = os.environ.copy()

    # Build afl with qemu (shared build code afl/afl++)
    afl_fuzzer_qemu.build()

    # Next, build a binary for Eclipser.
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    eclipser_outdir = get_eclipser_outdir(os.environ['OUT'])
    os.mkdir(eclipser_outdir)
    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['CFLAGS'] = ' '.join(utils.NO_SANITIZER_COMPAT_CFLAGS)
    cxxflags = [utils.LIBCPLUSPLUS_FLAG] + utils.NO_SANITIZER_COMPAT_CFLAGS
    new_env['CXXFLAGS'] = ' '.join(cxxflags)
    new_env['OUT'] = eclipser_outdir
    new_env['FUZZER_LIB'] = '/libStandaloneFuzzTarget.a'
    new_env['FUZZ_TARGET'] = os.path.join(
        eclipser_outdir, os.path.basename(os.getenv('FUZZ_TARGET')))
    print('[build] Re-building benchmark for eclipser fuzzing target.')
    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=new_env)


def eclipser(input_corpus, output_corpus, target_binary):
    """Run Eclipser."""
    # We will use output_corpus as a directory where AFL and Eclipser sync their
    # test cases with each other. For Eclipser, we should explicitly specify an
    # output directory under this sync directory.
    eclipser_out = os.path.join(output_corpus, "eclipser_output")
    command = [
        'dotnet',
        '/Eclipser/build/Eclipser.dll',
        '-p',
        target_binary,
        '-s',
        output_corpus,
        '-o',
        eclipser_out,
        '--arg',  # Specifies the command-line of the program.
        'foo',
        '-f',  # Specifies the path of file input to fuzz.
        'foo',
        '-v',  # Controls the verbosity.
        '2',
        '--exectimeout',
        '5000',
    ]
    if os.listdir(input_corpus):  # Specify inputs only if any seed exists.
        command += ['-i', input_corpus]
    print('[eclipser] Run Eclipser with command: ' + ' '.join(command))
    subprocess.Popen(command)


def afl_worker(input_corpus, output_corpus, target_binary):
    """Run AFL worker instance."""
    print('[afl_worker] Run AFL worker')
    afl_fuzzer.run_afl_fuzz(input_corpus, output_corpus, target_binary,
                            ['-Q', '-S', 'afl-worker'], True)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""

    # Calculate eclipser binary path from the afl target binary.
    target_binary_directory = os.path.dirname(target_binary)
    eclipser_target_binary_directory = (
        get_eclipser_outdir(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    eclipser_target_binary = os.path.join(eclipser_target_binary_directory,
                                          target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    afl_args = (input_corpus, output_corpus, target_binary)
    eclipser_args = (input_corpus, output_corpus, eclipser_target_binary)
    # Do not launch AFL master instance for now, to reduce memory usage and
    # align with the vanilla AFL.
    print('[fuzz] Running AFL worker')
    afl_worker_thread = threading.Thread(target=afl_worker, args=afl_args)
    afl_worker_thread.start()
    print('[fuzz] Running Eclipser')
    eclipser_thread = threading.Thread(target=eclipser, args=eclipser_args)
    eclipser_thread.start()
    print('[fuzz] Now waiting for threads to finish...')
    afl_worker_thread.join()
    eclipser_thread.join()
