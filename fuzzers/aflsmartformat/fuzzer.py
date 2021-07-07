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
"""Integration code for AFLSmartFormat fuzzer."""

import os
import shutil
import subprocess

from fuzzers.afl import fuzzer as afl_fuzzer


def get_format():
    """Identify format used by benchmark."""
    input_model = ''
    benchmark_name = os.environ['BENCHMARK']
    if benchmark_name == 'libpng-1.2.56':
        input_model = 'png'
    if benchmark_name == 'libpcap_fuzz_both':
        input_model = 'pcap'
    if benchmark_name == 'libjpeg-turbo-07-2017':
        input_model = 'jpg'
    if benchmark_name == 'vorbis-2017-12-11':
        input_model = 'ogg-orig'
    if benchmark_name == 'bloaty_fuzz_target':
        input_model = 'elf-orig'
    # if benchmark_name == 'libarchive_libarchive_fuzzer':
    #     input_model = 'zip'
    # if benchmark_name == 'ffmpeg_ffmpeg_demuxer_fuzzer':
    #     input_model = 'mp4'

    return input_model


def build():
    """Build format-specific fuzzer."""
    input_model = get_format()

    if input_model:
        print('Building {fmt}-fuzzer'.format(fmt=input_model))
        subprocess.check_call(
            ['/bin/bash', '-ex', '/FormatFuzzer/build.sh', input_model],
            cwd='/FormatFuzzer')

    # Build benchmark.
    afl_fuzzer.build()

    # Copy Format-specific fuzzer to OUT.
    if input_model:
        print('[post_build] Copying {fmt}-fuzzer to $OUT directory'.format(
            fmt=input_model))
        shutil.copy('/FormatFuzzer/{fmt}-fuzzer'.format(fmt=input_model),
                    os.environ['OUT'])
        shutil.copy('/afl/parser.sh', os.environ['OUT'])


def fuzz(input_corpus, output_corpus, target_binary):
    """Run afl-fuzz on target."""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    os.environ['PATH'] += os.pathsep + '/out'

    composite_mode = False

    input_model = get_format()
    os.environ['FORMAT_FUZZER'] = '{fmt}-fuzzer'.format(fmt=input_model)

    additional_flags = [
        # Enable stacked mutations
        '-h',
        # Enable structure-aware fuzzing
        '-w',
        'peach',
        # Select input model
        '-g',
        '{fmt}-fuzzer'.format(fmt=input_model),
    ]

    # Enable composite mode for targets
    # taking multiple input formats like bloaty
    if composite_mode:
        additional_flags.append('-c')

    if input_model != '':
        afl_fuzzer.run_afl_fuzz(input_corpus, output_corpus, target_binary,
                                additional_flags)
    else:
        afl_fuzzer.run_afl_fuzz(input_corpus, output_corpus, target_binary)
