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
"""Integration code for AFLcc fuzzer."""

import shutil
import os
import threading
import subprocess

from fuzzers import utils

from fuzzers.afl import fuzzer as afl_fuzzer


def is_benchmark(name):
    """Check if the benchmark contains the string |name|"""
    benchmark = os.getenv('BENCHMARK', None)
    return benchmark is not None and name in benchmark


def openthread_suppress_error_flags():
    """Suppress errors for openthread"""
    return [
        '-Wno-error=embedded-directive',
        '-Wno-error=gnu-zero-variadic-macro-arguments',
        '-Wno-error=overlength-strings', '-Wno-error=c++11-long-long',
        '-Wno-error=c++11-extensions', '-Wno-error=variadic-macros'
    ]


def libjpeg_turbo_asm_object_files():
    """
        Additional .o files compiled from .asm files
        and absent from the LLVM .bc file we extracted
        TODO(laurentsimon): check if we can link against
        *.a instead of providing a list of .o files
    """
    return [
        './BUILD/simd/jidctred-sse2-64.o', './BUILD/simd/jidctint-sse2-64.o',
        './BUILD/simd/jidctfst-sse2-64.o', './BUILD/simd/jdmerge-sse2-64.o',
        './BUILD/simd/jidctflt-sse2-64.o', './BUILD/simd/jdsample-sse2-64.o',
        './BUILD/simd/jdcolor-sse2-64.o'
    ]


def fix_fuzzer_lib():
    """Fix FUZZER_LIB for certain benchmarks"""

    if '--warn-unresolved-symbols' not in os.environ['CFLAGS']:
        os.environ['FUZZER_LIB'] += ' -L/ -lAflccMock -lpthread'

    if is_benchmark('curl'):
        shutil.copy('/libAflccMock.so', '/usr/lib/libAflccMock.so')

    if is_benchmark('systemd'):
        shutil.copy('/libAFL.a', '/usr/lib/libFuzzingEngine.a')
        ld_flags = ['-lpthread']
        utils.append_flags('LDFLAGS', ld_flags)


def add_compilation_cflags():
    """Add custom flags for certain benchmarks"""
    if is_benchmark('openthread'):
        openthread_flags = openthread_suppress_error_flags()
        utils.append_flags('CFLAGS', openthread_flags)
        utils.append_flags('CXXFLAGS', openthread_flags)

    elif is_benchmark('php'):
        php_flags = ['-D__builtin_cpu_supports\\(x\\)=0']
        utils.append_flags('CFLAGS', php_flags)
        utils.append_flags('CXXFLAGS', php_flags)

    # For some benchmarks, we also tell the compiler
    # to ignore unresolved symbols. This is useful when we cannot change
    # the build process to add a shared library for linking
    # (which contains mocked functions: libAflccMock.so).
    # Note that some functions are only defined post-compilation
    # during the LLVM passes.
    elif is_benchmark('bloaty') or is_benchmark('openssl') or is_benchmark(
            'systemd'):
        unresolved_flags = ['-Wl,--warn-unresolved-symbols']
        utils.append_flags('CFLAGS', unresolved_flags)
        utils.append_flags('CXXFLAGS', unresolved_flags)

    elif is_benchmark('curl'):
        dl_flags = ['-ldl', '-lpsl']
        utils.append_flags('CFLAGS', dl_flags)
        utils.append_flags('CXXFLAGS', dl_flags)


def add_post_compilation_lflags(ldflags_arr):
    """Add additional linking flags for certain benchmarks"""
    if is_benchmark('libjpeg'):
        ldflags_arr += libjpeg_turbo_asm_object_files()
    elif is_benchmark('php'):
        ldflags_arr += ['-lresolv']
    elif is_benchmark('curl'):
        ldflags_arr += [
            '-ldl', '-lpsl', '/src/openssl/libcrypto.a', '/src/openssl/libssl.a'
        ]
    elif is_benchmark('openssl'):
        ldflags_arr += ['/src/openssl/libcrypto.a', '/src/openssl/libssl.a']
    elif is_benchmark('systemd'):
        shutil.copy(
            os.path.join(os.environ['OUT'],
                         'src/shared/libsystemd-shared-245.so'),
            '/usr/lib/libsystemd-shared-245.so')
        ldflags_arr += ['-lsystemd-shared-245']


def prepare_fuzz_environment(input_corpus):
    """Prepare run for some benchmarks"""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    # OUT env variable does not exists, it seems.
    if os.path.isfile('/out/src/shared/libsystemd-shared-245.so'):
        shutil.copy('/out/src/shared/libsystemd-shared-245.so',
                    '/usr/lib/libsystemd-shared-245.so')


def prepare_build_environment():
    """Set environment variables used to build benchmark."""
    # Update compiler flags for clang-3.8.
    cflags = ['-fPIC']
    cppflags = cflags + [
        '-I/usr/local/include/c++/v1/', '-stdlib=libc++', '-std=c++11'
    ]
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cppflags)

    # Add flags for various benchmarks.
    add_compilation_cflags()

    # Setup aflcc compiler.
    os.environ['LLVM_CONFIG'] = 'llvm-config-3.8'
    os.environ['CC'] = '/afl/aflc-gclang'
    os.environ['CXX'] = '/afl/aflc-gclang++'
    os.environ['FUZZER_LIB'] = '/libAFL.a'

    # Fix FUZZER_LIB for various benchmarks.
    fix_fuzzer_lib()


def post_build(fuzz_target):
    """Perform the post-processing for a target"""
    print(f'Fuzz-target: {fuzz_target}')

    getbc_cmd = f'/afl/aflc-get-bc {fuzz_target}'
    if os.system(getbc_cmd) != 0:
        raise ValueError('get-bc failed')

    # Set the flags. ldflags is here temporarily until the benchmarks
    # are cleaned up and standalone.
    cppflags_arr = [
        '-I/usr/local/include/c++/v1/', '-stdlib=libc++', '-std=c++11'
    ]
    # Note: -ld for dlopen(), -lbsd for strlcpy().
    ldflags_arr = [
        '-lpthread', '-lm', ' -lz', '-larchive', '-lglib-2.0', '-ldl', '-lbsd'
    ]

    # Add post compilation linking flags for certain benchmarks.
    add_post_compilation_lflags(ldflags_arr)

    # Stringify the flags arrays.
    cppflags = ' '.join(cppflags_arr)
    ldflags = ' '.join(ldflags_arr)

    # Create the different build types.
    os.environ['AFL_BUILD_TYPE'] = 'FUZZING'

    # The original afl binary.
    print('[post_build] Generating original afl build')
    os.environ['AFL_COVERAGE_TYPE'] = 'ORIGINAL'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'NONE'
    os.environ['AFL_DICT_TYPE'] = 'NORMAL'
    bin1_cmd = '{compiler} {flags} -O3 {target}.bc -o ' \
    '{target}-original {ldflags}'.format(
        compiler='/afl/aflc-clang-fast++',
        flags=cppflags,
        target=fuzz_target,
        ldflags=ldflags)
    if os.system(bin1_cmd) != 0:
        raise ValueError(f'command "{bin1_cmd}" failed')

    # The normalized build with non-optimized dictionary.
    print('[post_build] Generating normalized-none-nopt')
    os.environ['AFL_COVERAGE_TYPE'] = 'ORIGINAL'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'NONE'
    os.environ['AFL_DICT_TYPE'] = 'NORMAL'
    bin2_cmd = '{compiler} {flags} {target}.bc -o ' \
    '{target}-normalized-none-nopt {ldflags}'.format(
        compiler='/afl/aflc-clang-fast++',
        flags=cppflags,
        target=fuzz_target,
        ldflags=ldflags)
    if os.system(bin2_cmd) != 0:
        raise ValueError(f'command "{bin2_cmd}" failed')

    # The no-collision split-condition optimized dictionary.
    print('[post_build] Generating no-collision-all-opt build')
    os.environ['AFL_COVERAGE_TYPE'] = 'NO_COLLISION'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'ALL'
    os.environ['AFL_DICT_TYPE'] = 'OPTIMIZED'
    bin3_cmd = '{compiler} {flags} {target}.bc -o ' \
    '{target}-no-collision-all-opt {ldflags}'.format(
        compiler='/afl/aflc-clang-fast++',
        flags=cppflags,
        target=fuzz_target,
        ldflags=ldflags)
    if os.system(bin3_cmd) != 0:
        raise ValueError(f'command "{bin3_cmd}" failed')

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/afl/afl-fuzz', os.environ['OUT'])


def build():
    """Build benchmark."""
    prepare_build_environment()

    utils.build_benchmark()

    print('[post_build] Extracting .bc file')
    fuzz_target = os.getenv('FUZZ_TARGET')
    fuzz_target_path = os.path.join(os.environ['OUT'], fuzz_target)
    post_build(fuzz_target_path)


def run_fuzzer(input_corpus,
               output_corpus,
               target_binary,
               additional_flags=None,
               hide_output=False):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    # FIXME: Currently AFL will exit if it encounters a crashing input in seed
    # corpus (usually timeouts). Add a way to skip/delete such inputs and
    # re-run AFL.
    print('[run_fuzzer] Running target with afl-fuzz')
    command = [
        './afl-fuzz',
        '-i',
        input_corpus,
        '-o',
        output_corpus,
        # Use no memory limit as ASAN doesn't play nicely with one.
        '-m',
        'none'
    ]
    if additional_flags:
        command.extend(additional_flags)
    dictionary_path = utils.get_dictionary_path(target_binary)
    if dictionary_path:
        command.extend(['-x', dictionary_path])
    command += [
        '--',
        target_binary,
        # Pass INT_MAX to afl the maximize the number of persistent loops it
        # performs.
        '2147483647'
    ]
    print('[run_fuzzer] Running command: ' + ' '.join(command))
    output_stream = subprocess.DEVNULL if hide_output else None
    subprocess.check_call(command, stdout=output_stream, stderr=output_stream)


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""
    prepare_fuzz_environment(input_corpus)

    # Note: dictionary automatically added by run_fuzzer().

    # Use a dictionary for original afl as well.
    print('[fuzz] Running AFL for original binary')
    src_file = f'{target_binary}-normalized-none-nopt.dict'
    dst_file = f'{target_binary}-original.dict'
    shutil.copy(src_file, dst_file)
    # Instead of generating a new dict, just hack this one
    # to be non-optimized to prevent AFL from aborting.
    os.system(f'sed -i \'s/OPTIMIZED/NORMAL/g\' {dst_file}')
    afl_fuzz_thread1 = threading.Thread(target=run_fuzzer,
                                        args=(input_corpus, output_corpus,
                                              f'{target_binary}-original',
                                              ['-S', 'secondary-original']))
    afl_fuzz_thread1.start()

    print('[run_fuzzer] Running AFL for normalized and optimized dictionary')
    afl_fuzz_thread2 = threading.Thread(
        target=run_fuzzer,
        args=(input_corpus, output_corpus,
              f'{target_binary}-normalized-none-nopt',
              ['-S', 'secondary-normalized-nopt']))
    afl_fuzz_thread2.start()

    print('[run_fuzzer] Running AFL for FBSP and optimized dictionary')
    run_fuzzer(input_corpus,
               output_corpus,
               f'{target_binary}-no-collision-all-opt',
               ['-S', 'secondary-no-collision-all-opt'],
               hide_output=False)
