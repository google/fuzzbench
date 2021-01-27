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

import os
import shutil
import subprocess
import time
import signal

from fuzzers import utils

WARMUP = 60 * 60


def prepare_build_environment():
    """Set environment variables used to build targets for AFL-based
    fuzzers."""
    cflags = ['-O2', '-fno-omit-frame-pointer']
    # ASAN?
    # cflags = ['-fsanitize-coverage=trace-pc-guard', '-fsanitize=address']
    utils.set_compilation_flags()
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)
    os.environ['CC'] = '/afl/afl-clang'
    os.environ['CXX'] = '/afl/afl-clang++'
    os.environ['FUZZER_LIB'] = '/libNeuzz.a'


def build():
    """Build benchmark."""
    prepare_build_environment()
    utils.build_benchmark()
    output_directory = os.environ['OUT']
    # Copy out the afl-fuzz binary as a build artifact.
    print('[post_build] Copying afl-fuzz to $OUT directory')
    shutil.copy('/afl/afl-fuzz', output_directory)
    # Neuzz also requires afl-showmap.
    print('[post_build] Copying afl-showmap to $OUT directory')
    shutil.copy('/afl/afl-showmap', output_directory)
    # Copy the Neuzz fuzzer itself.
    print('[post_build] Copy neuzz fuzzer.')
    shutil.copy('/neuzz/neuzz', output_directory)
    shutil.copy('/neuzz/nn.py', output_directory)


def prepare_fuzz_environment(input_corpus):
    """Prepare to fuzz with AFL or another AFL-based fuzzer."""
    # Tell AFL to not use its terminal UI so we get usable logs.
    os.environ['AFL_NO_UI'] = '1'
    # Skip AFL's CPU frequency check (fails on Docker).
    os.environ['AFL_SKIP_CPUFREQ'] = '1'
    # No need to bind affinity to one core, Docker enforces 1 core usage.
    os.environ['AFL_NO_AFFINITY'] = '1'
    # AFL will abort on startup if the core pattern sends notifications to
    # external programs. We don't care about this.
    os.environ['AFL_I_DONT_CARE_ABOUT_MISSING_CRASHES'] = '1'
    # Don't exit when crashes are found. This can happen when corpus from
    # OSS-Fuzz is used.
    os.environ['AFL_SKIP_CRASHES'] = '1'
    # Shuffle the queue
    os.environ['AFL_SHUFFLE_QUEUE'] = '1'

    # AFL needs at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)


def run_neuzz(input_corpus,
              output_corpus,
              target_binary,
              additional_flags=None,
              hide_output=False):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    print('[run_neuzz] Running target with afl-fuzz')
    command = [
        './afl-fuzz',
        '-i',
        input_corpus,
        '-o',
        output_corpus,
        # Use no memory limit as ASAN doesn't play nicely with one.
        '-m',
        'none',
        '-t',
        '1000+'
    ]
    print(f'[run_neuzz] Ignoring additional flags: {additional_flags}')
    command += ['--', target_binary]
    print('[run_neuzz] Running command: ' + ' '.join(command))
    output_stream = subprocess.DEVNULL if hide_output else None

    proc = subprocess.Popen(command,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)

    # subprocess.check_call(command, stdout=output_stream, stderr=output_stream)
    time.sleep(WARMUP)
    proc.send_signal(signal.SIGINT)

    print("[run_neuzz] Warmed up!")
    command = [
        "cp", "-RT", f"{output_corpus}/queue/", f"{input_corpus}_neuzzin/"
    ]
    print('[run_neuzz] Running command: ' + ' '.join(command))
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.check_call(command, stdout=output_stream, stderr=output_stream)

    afl_output_dir = os.path.join(output_corpus, 'queue')
    neuzz_input_dir = os.path.join(output_corpus, 'neuzz_in')
    # Treat afl's queue folder as the input for Neuzz.
    os.rename(afl_output_dir, neuzz_input_dir)

    command = [
        "python2", "./nn.py", '--output-folder', afl_output_dir, target_binary
    ]
    print('[run_neuzz] Running command: ' + ' '.join(command))
    subprocess.Popen(command, stdout=output_stream, stderr=output_stream)
    time.sleep(40)
    target_rel_path = os.path.relpath(target_binary, os.getcwd())
    command = [
        "./neuzz", "-m", "none", "-i", neuzz_input_dir, "-o", afl_output_dir,
        target_rel_path, "@@"
    ]
    print('[run_neuzz] Running command: ' + ' '.join(command))
    neuzz_proc = subprocess.Popen(command,
                                  stdout=output_stream,
                                  stderr=output_stream)
    neuzz_proc.wait()


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    prepare_fuzz_environment(input_corpus)
    run_neuzz(input_corpus, output_corpus, target_binary)
