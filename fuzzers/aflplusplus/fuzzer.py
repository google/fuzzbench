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
"""Integration code for AFLplusplus fuzzer."""

import os
import shutil

from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers import utils


def get_cmplog_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'cmplog')


def build(*args):  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    # BUILD_MODES is not already supported by fuzzbench, meanwhile we provide
    # a default configuration.
    build_modes = list(args)
    if 'BUILD_MODES' in os.environ:
        build_modes = os.environ['BUILD_MODES'].split(',')

    build_directory = os.environ['OUT']

    # If nothing was set this is the default:
    if not build_modes:
        build_modes = ['tracepc', 'cmplog']

    # Instrumentation coverage modes:
    if 'lto' in build_modes:
        os.environ['CC'] = '/afl/afl-clang-lto'
        os.environ['CXX'] = '/afl/afl-clang-lto++'
        os.environ['RANLIB'] = 'llvm-ranlib-11'
        os.environ['AR'] = 'llvm-ar-11'
        os.environ['AS'] = 'llvm-as-11'
    elif 'qemu' in build_modes:
        os.environ['CC'] = 'clang'
        os.environ['CXX'] = 'clang++'
    else:
        os.environ['CC'] = '/afl/afl-clang-fast'
        os.environ['CXX'] = '/afl/afl-clang-fast++'

    if 'instrim' in build_modes:
        # We dont set AFL_LLVM_INSTRIM_LOOPHEAD for better coverage
        os.environ['AFL_LLVM_INSTRIM'] = '1'
    elif 'tracepc' in build_modes or 'pcguard' in build_modes:
        os.environ['AFL_LLVM_USE_TRACE_PC'] = '1'
    elif 'classic' in build_modes:
        os.environ['AFL_LLVM_INSTRUMENT'] = 'CLASSIC'

    # Instrumentation coverage options:
    # Do not use a fixed map location (LTO only)
    if 'dynamic' in build_modes:
        os.environ['AFL_LLVM_MAP_DYNAMIC'] = '1'
    # Use a fixed map location (LTO only)
    if 'fixed' in build_modes:
        os.environ['AFL_LLVM_MAP_ADDR'] = '0x10000'
    # Skip over single block functions
    if 'skipsingle' in build_modes:
        os.environ['AFL_LLVM_SKIPSINGLEBLOCK'] = '1'
    # Enable context sentitivity for LLVM mode (non LTO only)
    if 'ctx' in build_modes:
        os.environ['AFL_LLVM_CTX'] = '1'
    # Enable N-gram coverage for LLVM mode (non LTO only)
    if 'ngram2' in build_modes:
        os.environ['AFL_LLVM_NGRAM_SIZE'] = '2'
    elif 'ngram3' in build_modes:
        os.environ['AFL_LLVM_NGRAM_SIZE'] = '3'
    elif 'ngram4' in build_modes:
        os.environ['AFL_LLVM_NGRAM_SIZE'] = '4'
    elif 'ngram5' in build_modes:
        os.environ['AFL_LLVM_NGRAM_SIZE'] = '5'
    elif 'ngram6' in build_modes:
        os.environ['AFL_LLVM_NGRAM_SIZE'] = '6'
    elif 'ngram7' in build_modes:
        os.environ['AFL_LLVM_NGRAM_SIZE'] = '7'
    elif 'ngram8' in build_modes:
        os.environ['AFL_LLVM_NGRAM_SIZE'] = '8'
    elif 'ngram16' in build_modes:
        os.environ['AFL_LLVM_NGRAM_SIZE'] = '16'

    # Further instrumentation options:
    # Disable neverZero implementation
    if 'nozero' in build_modes:
        os.environ['AFL_LLVM_SKIP_NEVERZERO'] = '1'

    # Only one of the following OR cmplog
    # enable laf-intel compare splitting
    if 'laf' in build_modes:
        os.environ['AFL_LLVM_LAF_SPLIT_SWITCHES'] = '1'
        os.environ['AFL_LLVM_LAF_SPLIT_COMPARES'] = '1'
        os.environ['AFL_LLVM_LAF_SPLIT_FLOATS'] = '1'
        if 'autodict' not in build_modes:
            os.environ['AFL_LLVM_LAF_TRANSFORM_COMPARES'] = '1'
    # enable auto dictionary for LTO
    if 'autodict' in build_modes:
        os.environ['AFL_LLVM_LTO_AUTODICTIONARY'] = '1'

    os.environ['FUZZER_LIB'] = '/libAFLDriver.a'

    # Some benchmarks like lcms
    # (see: https://github.com/mm2/Little-CMS/commit/ab1093539b4287c233aca6a3cf53b234faceb792#diff-f0e6d05e72548974e852e8e55dffc4ccR212)
    # fail to compile if the compiler outputs things to stderr in unexpected
    # cases. Prevent these failures by using AFL_QUIET to stop afl-clang-fast
    # from writing AFL specific messages to stderr.
    os.environ['AFL_QUIET'] = '1'
    os.environ['AFL_MAP_SIZE'] = '900000'

    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark()

    if 'cmplog' in build_modes and 'qemu' not in build_modes:

        # CmpLog requires an build with different instrumentation.
        new_env = os.environ.copy()
        new_env['AFL_LLVM_CMPLOG'] = '1'

        # For CmpLog build, set the OUT and FUZZ_TARGET environment
        # variable to point to the new CmpLog build directory.
        cmplog_build_directory = get_cmplog_build_directory(build_directory)
        os.mkdir(cmplog_build_directory)
        new_env['OUT'] = cmplog_build_directory
        fuzz_target = os.getenv('FUZZ_TARGET')
        if fuzz_target:
            new_env['FUZZ_TARGET'] = os.path.join(cmplog_build_directory,
                                                  os.path.basename(fuzz_target))

        print('Re-building benchmark for CmpLog fuzzing target')
        utils.build_benchmark(env=new_env)

    shutil.copy('/afl/afl-fuzz', build_directory)
    if os.path.exists('/afl/afl-qemu-trace'):
        shutil.copy('/afl/afl-qemu-trace', build_directory)
    if os.path.exists('/aflpp_qemu_driver_hook.so'):
        shutil.copy('/aflpp_qemu_driver_hook.so', build_directory)


def fuzz(input_corpus, output_corpus, target_binary, flags=tuple()):
    """Run fuzzer."""
    # Calculate CmpLog binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    cmplog_target_binary_directory = (
        get_cmplog_build_directory(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    cmplog_target_binary = os.path.join(cmplog_target_binary_directory,
                                        target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    # decomment this to enable libdislocator
    # os.environ['AFL_ALIGNED_ALLOC'] = '1' # align malloc to max_align_t
    # os.environ['AFL_PRELOAD'] = '/afl/libdislocator.so'

    flags = list(flags)
    if not flags or not flags[0] == '-Q':  # work around for afl-qemu
        flags += ['-p', 'seek']
    if os.path.exists(cmplog_target_binary):
        flags += ['-c', cmplog_target_binary]
    if 'ADDITIONAL_ARGS' in os.environ:
        flags += os.environ['ADDITIONAL_ARGS'].split(' ')

    afl_fuzzer.run_afl_fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            additional_flags=flags)
