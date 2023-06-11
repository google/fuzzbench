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
"""Integration code for Collabtive Fuzzer Framework."""

import os
import shutil
import subprocess

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer
def get_cmplog_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'cmplog')


def get_uninstrumented_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'uninstrumented')

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

    os.environ['AFL_IGNORE_UNKNOWN_ENVS'] = '1'
    os.environ['AFL_FAST_CAL'] = '1'
    os.environ['AFL_NO_WARN_INSTABILITY'] = '1'
    os.environ['AFL_CMPLOG_ONLY_NEW'] = '1'
    os.environ['AFL_LLVM_DICT2FILE_NO_MAIN'] = '1'
    os.environ['AFL_CUSTOM_MUTATOR_LIBRARY'] = '/out/aflplusplus/autotokens.so'
    os.environ['AUTOTOKENS_FUZZ_COUNT_SHIFT'] = '1'
    os.environ['AUTOTOKENS_AUTO_DISABLE'] = '1'
    os.environ['AUTOTOKENS_ONLY_FAV'] = '1'
    os.environ['AUTOTOKENS_LEARN_DICT'] = '2'
    os.environ['AFL_NO_AFFINITY'] = '1'

    # AFL needs at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)

def get_aflpp_target_dir(output_directory):
    """Return path to AFL++'s target directory."""
    return os.path.join(output_directory, 'aflplusplus')

def get_afl_target_dir(output_directory):
    """Return path to AFL's target directory."""
    return os.path.join(output_directory, 'afl')

def get_darwin_target_dir(output_directory):
    """Return path to darwin's target directory."""
    return os.path.join(output_directory, 'darwin')

def get_ecofuzz_target_dir(output_directory):
    """Return path to ecofuzz's target directory."""
    return os.path.join(output_directory, 'ecofuzz')

def get_entropic_target_dir(output_directory):
    """Return path to entropic's target directory."""
    return os.path.join(output_directory, 'entropic')

def get_fafuzz_target_dir(output_directory):
    """Return path to fafuzz's target directory."""
    return os.path.join(output_directory, 'fafuzz')

def get_fairfuzz_target_dir(output_directory):
    """Return path to fairfuzz's target directory."""
    return os.path.join(output_directory, 'fairfuzz')

def get_hastefuzz_target_dir(output_directory):
    """Return path to hastefuzz's target directory."""
    return os.path.join(output_directory, 'hastefuzz')

def get_libfuzzer_target_dir(output_directory):
    """Return path to libfuzzer's target directory."""
    return os.path.join(output_directory, 'libfuzzer')

def get_mopt_target_dir(output_directory):
    """Return path to mopt's target directory."""
    return os.path.join(output_directory, 'mopt')

def get_wingfuzz_target_dir(output_directory):
    """Return path to wingfuzz's target directory."""
    return os.path.join(output_directory, 'wingfuzz')

def get_honggfuzz_target_dir(output_directory):
    """Return path to Honggfuzz's target directory."""
    return os.path.join(output_directory, 'honggfuzz')

def afl_build():
    """Build benchmark."""
    new_env = os.environ.copy()    
    cflags = ['-fsanitize-coverage=trace-pc-guard']
    utils.append_flags('CFLAGS', cflags, new_env)
    utils.append_flags('CXXFLAGS', cflags, new_env)

    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libAFL.a'
    utils.build_benchmark(env=new_env)

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/afl/afl-fuzz', new_env['OUT'])

def darwin_build():
    """Build benchmark."""
    new_env = os.environ.copy()
    cflags = ['-fsanitize-coverage=trace-pc-guard']
    utils.append_flags('CFLAGS', cflags, new_env)
    utils.append_flags('CXXFLAGS', cflags, new_env)

    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libDARWIN.a'
    utils.build_benchmark(env=new_env)

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/darwin/afl-fuzz', os.environ['OUT'])

def ecofuzz_build():
    """Build benchmark."""
    new_env = os.environ.copy()
    cflags = ['-fsanitize-coverage=trace-pc-guard']
    utils.append_flags('CFLAGS', cflags, new_env)
    utils.append_flags('CXXFLAGS', cflags, new_env)

    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libECOFUZZ.a'
    utils.build_benchmark(env=new_env)

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/ecofuzz/afl-fuzz', os.environ['OUT'])

def entropic_build():
    """Build benchmark."""
    new_env = os.environ.copy()
    cflags = ['-fsanitize=fuzzer-no-link']
    utils.append_flags('CFLAGS', cflags, new_env)
    utils.append_flags('CXXFLAGS', cflags, new_env)

    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libENTROPIC.a'

    utils.build_benchmark(env=new_env)

def fafuzz_build():
    """Build benchmark."""
    new_env = os.environ.copy()
    cflags = ['-fsanitize-coverage=trace-pc-guard']
    utils.append_flags('CFLAGS', cflags, new_env)
    utils.append_flags('CXXFLAGS', cflags, new_env)

    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libFAFUZZ.a'
    utils.build_benchmark(env=new_env)

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/fafuzz/afl-fuzz', os.environ['OUT'])

def fairfuzz_build():
    """Build benchmark."""
    new_env = os.environ.copy()
    cflags = ['-fsanitize-coverage=trace-pc-guard']
    utils.append_flags('CFLAGS', cflags, new_env)
    utils.append_flags('CXXFLAGS', cflags, new_env)

    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libFAIRFUZZ.a'
    utils.build_benchmark(env=new_env)

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/fairfuzz/afl-fuzz', os.environ['OUT'])

def honggfuzz_build():
    """Build benchmark."""
    new_env = os.environ.copy()

    new_env['CC'] = '/honggfuzz/hfuzz_cc/hfuzz-clang'
    new_env['CXX'] = '/honggfuzz/hfuzz_cc/hfuzz-clang++'
    new_env['FUZZER_LIB'] = '/honggfuzz/empty_lib.o'

    utils.build_benchmark(env=new_env)

    print('[post_build] Copying honggfuzz to $OUT directory')
    # Copy over honggfuzz's main fuzzing binary.
    shutil.copy('/honggfuzz/honggfuzz', os.environ['OUT'])

def libfuzzer_build():
    """Build benchmark."""
    # With LibFuzzer we use -fsanitize=fuzzer-no-link for build CFLAGS and then
    # /usr/lib/libFuzzer.a as the FUZZER_LIB for the main fuzzing binary. This
    # allows us to link against a version of LibFuzzer that we specify.
    cflags = ['-fsanitize=fuzzer-no-link']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    new_env = os.environ.copy()
    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/usr/lib/libFuzzer.a'

    utils.build_benchmark(env=new_env)

def mopt_build():
    """Build benchmark."""
    new_env = os.environ.copy()
    cflags = ['-fsanitize-coverage=trace-pc-guard']
    utils.append_flags('CFLAGS', cflags, new_env)
    utils.append_flags('CXXFLAGS', cflags, new_env)

    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libMOPT.a'

    utils.build_benchmark(env=new_env)

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/mopt/afl-fuzz', new_env['OUT'])

def wingfuzz_build():
    """Build benchmark."""
    new_env = os.environ.copy()
    cflags = [
        '-fsanitize=fuzzer-no-link',
        '-fno-sanitize-coverage=trace-cmp',
        '-fno-legacy-pass-manager',
        '-fpass-plugin=/LoadCmpTracer.so',
        '-w',
        '-Wl,/WeakSym.o'
    ]
    utils.append_flags('CFLAGS', cflags, new_env)
    utils.append_flags('CXXFLAGS', cflags, new_env)

    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/libWingfuzz.a'
    utils.build_benchmark(env=new_env)

def aflplusplus_build(*args):  # pylint: disable=too-many-branches,too-many-statements
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
        build_modes = ['tracepc', 'cmplog', 'dict2file']

    # For bug type benchmarks we have to instrument via native clang pcguard :(
    build_flags = os.environ['CFLAGS']

    if build_flags.find(
            'array-bounds'
    ) != -1 and 'qemu' not in build_modes and 'classic' not in build_modes:
        if 'gcc' not in build_modes:
            build_modes[0] = 'native'

    # Instrumentation coverage modes:
    if 'lto' in build_modes:
        os.environ['CC'] = '/aflplusplus/afl-clang-lto'
        os.environ['CXX'] = '/aflplusplus/afl-clang-lto++'
        edge_file = build_directory + '/aflpp_edges.txt'
        os.environ['AFL_LLVM_DOCUMENT_IDS'] = edge_file
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
        if build_flags.find('array-bounds') != -1:
            os.environ['CFLAGS'] = '-fsanitize=address -O1'
            os.environ['CXXFLAGS'] = '-fsanitize=address -O1'
        else:
            os.environ['CFLAGS'] = ''
            os.environ['CXXFLAGS'] = ''
            os.environ['CPPFLAGS'] = ''
    else:
        os.environ['CC'] = '/aflplusplus/afl-clang-fast'
        os.environ['CXX'] = '/aflplusplus/afl-clang-fast++'

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
        os.environ['AFL_LLVM_DICT2FILE_NO_MAIN'] = '1'
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

    # Some benchmarks like lcms. (see:
    # https://github.com/mm2/Little-CMS/commit/ab1093539b4287c233aca6a3cf53b234faceb792#diff-f0e6d05e72548974e852e8e55dffc4ccR212)
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

    if 'symcc' in build_modes:

        symcc_build_directory = get_uninstrumented_build_directory(
            build_directory)
        os.mkdir(symcc_build_directory)

        # symcc requires an build with different instrumentation.
        new_env = os.environ.copy()
        new_env['CC'] = '/symcc/build/symcc'
        new_env['CXX'] = '/symcc/build/sym++'
        new_env['SYMCC_OUTPUT_DIR'] = '/tmp'
        new_env['CXXFLAGS'] = new_env['CXXFLAGS'].replace('-stlib=libc++', '')
        new_env['FUZZER_LIB'] = '/libfuzzer-harness.o'
        new_env['OUT'] = symcc_build_directory
        new_env['SYMCC_LIBCXX_PATH'] = '/libcxx_native_build'
        new_env['SYMCC_NO_SYMBOLIC_INPUT'] = '1'
        new_env['SYMCC_SILENT'] = '1'

        # For symcc build, set the OUT and FUZZ_TARGET environment
        # variable to point to the new symcc build directory.
        new_env['OUT'] = symcc_build_directory
        fuzz_target = os.getenv('FUZZ_TARGET')
        if fuzz_target:
            new_env['FUZZ_TARGET'] = os.path.join(symcc_build_directory,
                                                  os.path.basename(fuzz_target))

        print('Re-building benchmark for symcc fuzzing target')
        utils.build_benchmark(env=new_env)

    shutil.copy('/aflplusplus/afl-fuzz', build_directory)
    if os.path.exists('/aflplusplus/afl-qemu-trace'):
        shutil.copy('/aflplusplus/afl-qemu-trace', build_directory)
    if os.path.exists('/aflpp_qemu_driver_hook.so'):
        shutil.copy('/aflpp_qemu_driver_hook.so', build_directory)
    if os.path.exists('/get_frida_entry.sh'):
        shutil.copy('/aflplusplus/afl-frida-trace.so', build_directory)
        shutil.copy('/get_frida_entry.sh', build_directory)
    shutil.copy('/aflplusplus/autotokens.so', build_directory)


def build_aflpp():
    """Build benchmark with AFL++."""
    print('Building with AFL++')
    out_dir = os.environ['OUT']
    aflpp_target_dir = get_aflpp_target_dir(os.environ['OUT'])
    os.environ['OUT'] = aflpp_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')    
    with utils.restore_directory(src), utils.restore_directory(src):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        aflplusplus_build()
    os.environ['OUT'] = out_dir


def build_afl():
    """Build benchmark with AFL."""
    print('Building with AFL')
    out_dir = os.environ['OUT']
    afl_target_dir = get_afl_target_dir(os.environ['OUT'])
    os.environ['OUT'] = afl_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        afl_build()
    os.environ['OUT'] = out_dir

def build_darwin():
    """Build benchmark with darwin."""
    print('Building with darwin')
    out_dir = os.environ['OUT']
    darwin_target_dir = get_darwin_target_dir(os.environ['OUT'])
    os.environ['OUT'] = darwin_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        darwin_build()
    os.environ['OUT'] = out_dir



def build_ecofuzz():
    """Build benchmark with ecofuzz."""
    print('Building with ecofuzz')
    out_dir = os.environ['OUT']
    ecofuzz_target_dir = get_ecofuzz_target_dir(os.environ['OUT'])
    os.environ['OUT'] = ecofuzz_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        ecofuzz_build()
    os.environ['OUT'] = out_dir

def build_entropic():
    """Build benchmark with entropic."""
    print('Building with entropic')
    out_dir = os.environ['OUT']
    entropic_target_dir = get_entropic_target_dir(os.environ['OUT'])
    os.environ['OUT'] = entropic_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        entropic_build()
    os.environ['OUT'] = out_dir

def build_fafuzz():
    """Build benchmark with fafuzz."""
    print('Building with fafuzz')
    out_dir = os.environ['OUT']
    fafuzz_target_dir = get_fafuzz_target_dir(os.environ['OUT'])
    os.environ['OUT'] = fafuzz_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        fafuzz_build()
    os.environ['OUT'] = out_dir


def build_fairfuzz():
    """Build benchmark with fairfuzz."""
    print('Building with fairfuzz')
    out_dir = os.environ['OUT']
    fairfuzz_target_dir = get_fairfuzz_target_dir(os.environ['OUT'])
    os.environ['OUT'] = fairfuzz_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        fairfuzz_build()
    os.environ['OUT'] = out_dir



def build_libfuzzer():
    """Build benchmark with libfuzzer."""
    print('Building with libfuzzer')
    out_dir = os.environ['OUT']
    libfuzzer_target_dir = get_libfuzzer_target_dir(os.environ['OUT'])
    os.environ['OUT'] = libfuzzer_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        libfuzzer_build()
    os.environ['OUT'] = out_dir

def build_mopt():
    """Build benchmark with mopt."""
    print('Building with mopt')
    out_dir = os.environ['OUT']
    mopt_target_dir = get_mopt_target_dir(os.environ['OUT'])
    os.environ['OUT'] = mopt_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        mopt_build()
    os.environ['OUT'] = out_dir

def build_wingfuzz():
    """Build benchmark with wingfuzz."""
    print('Building with wingfuzz')
    out_dir = os.environ['OUT']
    wingfuzz_target_dir = get_wingfuzz_target_dir(os.environ['OUT'])
    os.environ['OUT'] = wingfuzz_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        wingfuzz_build()
    os.environ['OUT'] = out_dir                

def build_honggfuzz():
    """Build benchmark with Honggfuzz."""
    print('Building with Honggfuzz')
    out_dir = os.environ['OUT']
    honggfuzz_target_dir = get_honggfuzz_target_dir(os.environ['OUT'])
    os.environ['OUT'] = honggfuzz_target_dir
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        honggfuzz_build()
    os.environ['OUT'] = out_dir

def prepare_build_environment():
    """Prepare build environment."""
    aflpp_target_dir = get_aflpp_target_dir(os.environ['OUT'])
    honggfuzz_target_dir = get_honggfuzz_target_dir(os.environ['OUT'])
    afl_target_dir = get_afl_target_dir(os.environ['OUT'])
    darwin_target_dir = get_darwin_target_dir(os.environ['OUT'])
    ecofuzz_target_dir = get_ecofuzz_target_dir(os.environ['OUT'])
    entropic_target_dir = get_entropic_target_dir(os.environ['OUT'])
    fafuzz_target_dir = get_fafuzz_target_dir(os.environ['OUT'])
    fairfuzz_target_dir = get_fairfuzz_target_dir(os.environ['OUT'])
    hastefuzz_target_dir = get_hastefuzz_target_dir(os.environ['OUT'])
    libfuzzer_target_dir = get_libfuzzer_target_dir(os.environ['OUT'])
    mopt_target_dir = get_mopt_target_dir(os.environ['OUT'])
    wingfuzz_target_dir = get_wingfuzz_target_dir(os.environ['OUT'])

    os.makedirs(aflpp_target_dir, exist_ok=True)
    os.makedirs(honggfuzz_target_dir, exist_ok=True)
    os.makedirs(wingfuzz_target_dir, exist_ok=True)
    os.makedirs(afl_target_dir, exist_ok=True)
    os.makedirs(darwin_target_dir, exist_ok=True)
    os.makedirs(ecofuzz_target_dir, exist_ok=True)
    os.makedirs(entropic_target_dir, exist_ok=True)
    os.makedirs(fafuzz_target_dir, exist_ok=True)
    os.makedirs(fairfuzz_target_dir, exist_ok=True)
    os.makedirs(hastefuzz_target_dir, exist_ok=True)
    os.makedirs(libfuzzer_target_dir, exist_ok=True)
    os.makedirs(mopt_target_dir, exist_ok=True)


def build():
    """Build benchmark."""
    prepare_build_environment()
    new_env = os.environ.copy()
    cflags = ['-fsanitize=fuzzer-no-link']
    utils.append_flags('CFLAGS', cflags, env=new_env)
    utils.append_flags('CXXFLAGS', cflags, env=new_env)
    src = new_env.get('SRC')
    work = new_env.get('WORK')
    new_env['CC'] = 'clang'
    new_env['CXX'] = 'clang++'
    new_env['FUZZER_LIB'] = '/usr/lib/libHCFUZZER.a'
    with utils.restore_directory(src), utils.restore_directory(work):
        utils.build_benchmark(env=new_env)

    build_libfuzzer()
    #build_wingfuzz()
    #build_entropic()
    #build_honggfuzz()
    #build_afl()
    #build_darwin()
    #build_ecofuzz()
    #build_fafuzz()
    #build_fairfuzz()  
    #build_mopt()
    #build_aflpp()
    


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer. Wrapper that uses the defaults when calling
    run_fuzzer."""
    run_fuzzer(input_corpus,
               output_corpus,
               target_binary,
               extra_flags=['-keep_seed=0', '-cross_over_uniform_dist=1'])


def run_fuzzer(input_corpus, output_corpus, target_binary, extra_flags=None):
    """Run fuzzer."""
    if extra_flags is None:
        extra_flags = []

    # Seperate out corpus and crash directories as sub-directories of
    # |output_corpus| to avoid conflicts when corpus directory is reloaded.
    crashes_dir = os.path.join(output_corpus, 'crashes')
    output_corpus = os.path.join(output_corpus, 'corpus')
    os.makedirs(crashes_dir)
    os.makedirs(output_corpus)

    #prepare_fuzz_environment(input_corpus)
    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    binary = os.path.basename(target_binary)

    os.environ['AFL_IGNORE_UNKNOWN_ENVS'] = '1'
    os.environ['AFL_FAST_CAL'] = '1'
    os.environ['AFL_NO_WARN_INSTABILITY'] = '1'

    flags = [
        '-print_final_stats=1',
        # `close_fd_mask` to prevent too much logging output from the target.
        '-close_fd_mask=3',
        # Run in fork mode to allow ignoring ooms, timeouts, crashes and
        # continue fuzzing indefinitely.
        f'-target_program={binary}',
        '-fuzzers=libfuzzer',
        '-fork=1',
        '-fork_job_budget_coe=3',
        '-fork_num_seeds=3',
        '-fork_max_job_time=1800',
        '-ignore_ooms=1',
        '-ignore_timeouts=1',
        '-ignore_crashes=1',

        # Don't use LSAN's leak detection. Other fuzzers won't be using it and
        # using it will cause libFuzzer to find "crashes" no one cares about.
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
