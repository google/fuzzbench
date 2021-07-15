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


def get_unusual_build_directory(target_directory):
    """Return path to Unusual target directory."""
    return os.path.join(target_directory, 'unusual')


def build(*args):  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    # BUILD_MODES is not already supported by fuzzbench, meanwhile we provide
    # a default configuration.

    build_modes = list(args)
    if 'BUILD_MODES' in os.environ:
        build_modes = os.environ['BUILD_MODES'].split(',')

    # Placeholder comment.
    build_directory = os.environ['OUT']

    # If nothing was set this is the default:
    if not build_modes:
        build_modes = ['tracepc', 'dict2file']

    # For bug type benchmarks we have to instrument via native clang pcguard :(
    build_flags = os.environ['CFLAGS']
    if build_flags.find(
            'array-bounds'
    ) != -1 and 'qemu' not in build_modes and 'classic' not in build_modes:
        build_modes[0] = 'native'

    # Instrumentation coverage modes:
    if 'lto' in build_modes:
        os.environ['CC'] = '/afl/afl-clang-lto'
        os.environ['CXX'] = '/afl/afl-clang-lto++'
        if os.path.isfile('/usr/local/bin/llvm-ranlib-13'):
            os.environ['RANLIB'] = 'llvm-ranlib-13'
            os.environ['AR'] = 'llvm-ar-13'
            os.environ['AS'] = 'llvm-as-13'
        elif os.path.isfile('/usr/local/bin/llvm-ranlib-12'):
            os.environ['RANLIB'] = 'llvm-ranlib-12'
            os.environ['AR'] = 'llvm-ar-12'
            os.environ['AS'] = 'llvm-as-12'
        else:
            os.environ['RANLIB'] = 'llvm-ranlib'
            os.environ['AR'] = 'llvm-ar'
            os.environ['AS'] = 'llvm-as'
    elif 'qemu' in build_modes:
        os.environ['CC'] = 'clang'
        os.environ['CXX'] = 'clang++'
    elif 'gcc' in build_modes:
        os.environ['CC'] = 'afl-gcc-fast'
        os.environ['CXX'] = 'afl-g++-fast'
    elif 'symcc' in build_modes:
        os.environ['CC'] = '/symcc/build/symcc'
        os.environ['CXX'] = '/symcc/build/sym++'
        os.environ['SYMCC_OUTPUT_DIR'] = '/tmp'
        #os.environ['SYMCC_LIBCXX_PATH'] = '/libcxx_symcc_install'
    else:
        os.environ['CC'] = '/afl/afl-clang-fast'
        os.environ['CXX'] = '/afl/afl-clang-fast++'

    print('AFL++ build: ')
    print(build_modes)

    if 'qemu' in build_modes or 'symcc' in build_modes:
        os.environ['CFLAGS'] = ' '.join(utils.NO_SANITIZER_COMPAT_CFLAGS)
        cxxflags = [utils.LIBCPLUSPLUS_FLAG] + utils.NO_SANITIZER_COMPAT_CFLAGS
        os.environ['CXXFLAGS'] = ' '.join(cxxflags)

    if 'tracepc' in build_modes or 'pcguard' in build_modes:
        os.environ['AFL_LLVM_USE_TRACE_PC'] = '1'
    elif 'classic' in build_modes:
        os.environ['AFL_LLVM_INSTRUMENT'] = 'CLASSIC'
    elif 'native' in build_modes:
        os.environ['AFL_LLVM_INSTRUMENT'] = 'LLVMNATIVE'

    # Instrumentation coverage options:
    # Do not use a fixed map location (LTO only)
    if 'dynamic' in build_modes:
        os.environ['AFL_LLVM_MAP_DYNAMIC'] = '1'
    # Use a fixed map location (LTO only)
    if 'fixed' in build_modes:
        os.environ['AFL_LLVM_MAP_ADDR'] = '0x10000'
    # Generate an extra dictionary.
    if 'dict2file' in build_modes or 'native' in build_modes:
        os.environ['AFL_LLVM_DICT2FILE'] = build_directory + '/afl++.dict'
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
    if 'ctx1' in build_modes:
        os.environ['AFL_LLVM_CTX_K'] = '1'
    elif 'ctx2' in build_modes:
        os.environ['AFL_LLVM_CTX_K'] = '2'
    elif 'ctx3' in build_modes:
        os.environ['AFL_LLVM_CTX_K'] = '3'
    elif 'ctx4' in build_modes:
        os.environ['AFL_LLVM_CTX_K'] = '4'

    # Only one of the following OR cmplog
    # enable laf-intel compare splitting
    if 'laf' in build_modes:
        os.environ['AFL_LLVM_LAF_SPLIT_SWITCHES'] = '1'
        os.environ['AFL_LLVM_LAF_SPLIT_COMPARES'] = '1'
        os.environ['AFL_LLVM_LAF_SPLIT_FLOATS'] = '1'
        if 'autodict' not in build_modes:
            os.environ['AFL_LLVM_LAF_TRANSFORM_COMPARES'] = '1'

    if 'eclipser' in build_modes:
        os.environ['FUZZER_LIB'] = '/libStandaloneFuzzTarget.a'
    else:
        os.environ['FUZZER_LIB'] = '/libAFLDriver.a'

    # Some benchmarks like lcms
    # (see: https://github.com/mm2/Little-CMS/commit/ab1093539b4287c233aca6a3cf53b234faceb792#diff-f0e6d05e72548974e852e8e55dffc4ccR212)
    # fail to compile if the compiler outputs things to stderr in unexpected
    # cases. Prevent these failures by using AFL_QUIET to stop afl-clang-fast
    # from writing AFL specific messages to stderr.
    os.environ['AFL_QUIET'] = '1'
    os.environ['AFL_MAP_SIZE'] = '2621440'

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

    if 'unusual' in build_modes and 'qemu' not in build_modes:

        # Unusual requires an build with different instrumentation.
        new_env = os.environ.copy()
        new_env['AFL_LLVM_UNUSUAL_VALUES'] = '1'

        # For Unusual build, set the OUT and FUZZ_TARGET environment
        # variable to point to the new Unusual build directory.
        unusual_build_directory = get_unusual_build_directory(build_directory)
        os.mkdir(unusual_build_directory)
        new_env['OUT'] = unusual_build_directory
        fuzz_target = os.getenv('FUZZ_TARGET')
        if fuzz_target:
            new_env['FUZZ_TARGET'] = os.path.join(unusual_build_directory,
                                                  os.path.basename(fuzz_target))

        print('Re-building benchmark for Unusual fuzzing target')
        utils.build_benchmark(env=new_env)

    shutil.copy('/afl/afl-fuzz', build_directory)
    if os.path.exists('/afl/afl-qemu-trace'):
        shutil.copy('/afl/afl-qemu-trace', build_directory)
    if os.path.exists('/aflpp_qemu_driver_hook.so'):
        shutil.copy('/aflpp_qemu_driver_hook.so', build_directory)
    if os.path.exists('/get_frida_entry.sh'):
        shutil.copy('/afl/afl-frida-trace.so', build_directory)
        shutil.copy('/get_frida_entry.sh', build_directory)


def fuzz(input_corpus, output_corpus, target_binary, flags=tuple(), skip=False):
    """Run fuzzer."""
    # Calculate CmpLog binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    cmplog_target_binary_directory = (
        get_cmplog_build_directory(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    cmplog_target_binary = os.path.join(cmplog_target_binary_directory,
                                        target_binary_name)

    # Calculate Unusual binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    unusual_target_binary_directory = (
        get_unusual_build_directory(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    unusual_target_binary = os.path.join(unusual_target_binary_directory,
                                         target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    # decomment this to enable libdislocator.
    # os.environ['AFL_ALIGNED_ALLOC'] = '1' # align malloc to max_align_t
    # os.environ['AFL_PRELOAD'] = '/afl/libdislocator.so'
    os.environ['AFL_FAST_CAL'] = '1'

    flags = list(flags)

    if os.path.exists('./afl++.dict'):
        flags += ['-x', './afl++.dict']
    # Move the following to skip for upcoming _double tests:
    if os.path.exists(cmplog_target_binary):
        flags += ['-c', cmplog_target_binary]
    if os.path.exists(unusual_target_binary):
        flags += ['-u', unusual_target_binary]

    if not skip:
        if not flags or not flags[0] == '-Q' and '-p' not in flags:
            flags += ['-p', 'fast']
        if ((not flags or (not '-l' in flags and not '-R' in flags)) and
                os.path.exists(cmplog_target_binary)):
            flags += ['-l', '2']
        os.environ['AFL_DISABLE_TRIM'] = "1"
        if 'ADDITIONAL_ARGS' in os.environ:
            flags += os.environ['ADDITIONAL_ARGS'].split(' ')

    afl_fuzzer.run_afl_fuzz(input_corpus,
                            output_corpus,
                            target_binary,
                            additional_flags=flags)
