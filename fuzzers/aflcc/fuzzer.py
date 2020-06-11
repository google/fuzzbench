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
    """ Check if the benchmark contains the string 'name' """

    # TODO: return name in os.environ['BENCHMARK]
    # return benchmark is not None and name in benchmark

    # OSS-fuzz benchmarks do not have a consistent folder content
    # but typically have the name of the benchmark as part of the 
    # working directory.
    pwd_dir = os.getcwd()
    
    if name in pwd_dir:
        return True

    # Non-OSS-fuzz benchmarks.
    src_dir = os.environ['SRC']
    buildfile = os.path.join(src_dir, "benchmark/build.sh")
    if not os.path.isfile(buildfile):
        return False

    with open(buildfile, 'r') as file:
        content = file.read()
        if name in content:
            return True

    return False

def openthread_suppress_error_flags():
    """Suppress errors for openthread"""
    return ['-Wno-error=embedded-directive', 
            '-Wno-error=gnu-zero-variadic-macro-arguments', 
            '-Wno-error=overlength-strings', 
            '-Wno-error=c++11-long-long', 
            '-Wno-error=c++11-extensions', 
            '-Wno-error=variadic-macros']

def libjpeg_turbo_asm_object_files():
    """
        Additional .o files compiled from .asm files
        and absent from the LLVM .bc file we extracted
        TODO(laurentsimon): check if we can link against
        *.a instead of providing a list of .o files
    """
    return ['./BUILD/simd/jidctred-sse2-64.o',
            './BUILD/simd/jidctint-sse2-64.o',
            './BUILD/simd/jidctfst-sse2-64.o',
            './BUILD/simd/jdmerge-sse2-64.o',
            './BUILD/simd/jidctflt-sse2-64.o',
            './BUILD/simd/jdsample-sse2-64.o',
            './BUILD/simd/jdcolor-sse2-64.o']


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
    elif is_benchmark('bloaty') or is_benchmark('openssl') or is_benchmark('systemd'):
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
        ldflags_arr += ['-ldl', '-lpsl', '/src/openssl/libcrypto.a', '/src/openssl/libssl.a']
    elif is_benchmark('openssl'):
        ldflags_arr += ['/src/openssl/libcrypto.a', '/src/openssl/libssl.a']
    elif is_benchmark('systemd'):
        shutil.copy(os.path.join(os.environ['OUT'], 'src/shared/libsystemd-shared-245.so'), '/usr/lib/libsystemd-shared-245.so')
        ldflags_arr += ['-lsystemd-shared-245']

def prepare_fuzz_environment(input_corpus):
    """Prepare run for some benchmarks"""
    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    # OUT env variable does not exists, it seems.
    if os.path.isfile('/out/src/shared/libsystemd-shared-245.so'):
        shutil.copy('/out/src/shared/libsystemd-shared-245.so', '/usr/lib/libsystemd-shared-245.so')

def prepare_build_environment():
    """Set environment variables used to build benchmark."""
    utils.set_no_sanitizer_compilation_flags()

    # Update compiler flags for clang-3.8.
    cflags = ['-fPIC']
    cppflags = cflags + ['-I/usr/local/include/c++/v1/', 
                         '-stdlib=libc++', '-std=c++11']
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

def get_fuzz_targets():
    """Get the fuzz target name"""
    # For non oss-projects, FUZZ_TARGET contain the target binary.
    fuzz_target = os.getenv('FUZZ_TARGET', None)
    if fuzz_target is not None:
        return [fuzz_target]

    print('FUZZ_TARGET is not defined')

    # For these benchmarks, only return one file.
    targets = {'curl': 'curl_fuzzer_http', 
               'openssl': 'x509',
               'systemd': 'fuzz-link-parser',
               'php': 'php-fuzz-parser'}

    for target, fuzzname in targets.items():
        if is_benchmark(target):
            return [os.path.join(os.environ['OUT'], fuzzname)]

    # For the reamining oss-projects, use some heuristics.
    # We look for binaries in the OUT directory and take it as our targets.
    # Note that we may return multiple binaries: this is necessary because
    # sometimes multiple binaries are generated and we don't know which will
    # be used for fuzzing (e.g., zlib benchmark).
    # TODO(laurentsimon): hardcode targets for oss-fuzz projects in the 'targets' dictionary above.
    out_dir = os.environ['OUT']
    files = os.listdir(out_dir)
    fuzz_targets = []
    for filename in files:
        candidate_bin = os.path.join(out_dir, filename)
        if 'fuzz' in filename and os.access(candidate_bin, os.X_OK):
            fuzz_targets += [candidate_bin]

    if len(fuzz_targets) == 0:
        raise ValueError("Cannot find binary")
    return fuzz_targets

def post_build(fuzz_target):
    """Perform the post-processing for a target"""
    print('Fuzz-target: {target}'.format(target=fuzz_target))

    getbc_cmd = "/afl/aflc-get-bc {target}".format(target=fuzz_target)
    if os.system(getbc_cmd) != 0:
        raise ValueError("get-bc failed")

    # Set the flags. ldflags is here temporarily until the benchmarks
    # are cleaned up and standalone.
    cppflags_arr = ['-I/usr/local/include/c++/v1/', '-stdlib=libc++', '-std=c++11']
    # Note: -ld for dlopen(), -lbsd for strlcpy().
    ldflags_arr = ['-lpthread', '-lm', ' -lz', '-larchive', '-lglib-2.0', '-ldl', '-lbsd']

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
    bin1_cmd = "{compiler} {flags} -O3 {target}.bc -o {target}-original {ldflags}".format(compiler='/afl/aflc-clang-fast++', flags=cppflags, target=fuzz_target, ldflags=ldflags)
    if os.system(bin1_cmd) != 0:
        raise ValueError("command '{command}' failed".format(command=bin1_cmd))

    # The normalized build with non-optimized dictionary.
    print('[post_build] Generating normalized-none-nopt')
    os.environ['AFL_COVERAGE_TYPE'] = 'ORIGINAL'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'NONE'
    os.environ['AFL_DICT_TYPE'] = 'NORMAL'
    bin2_cmd = "{compiler} {flags} {target}.bc -o {target}-normalized-none-nopt {ldflags}".format(compiler='/afl/aflc-clang-fast++', flags=cppflags, target=fuzz_target, ldflags=ldflags)
    if os.system(bin2_cmd) != 0:
        raise ValueError("command '{command}' failed".format(command=bin2_cmd))

    # The no-collision split-condition optimized dictionary.
    print('[post_build] Generating no-collision-all-opt build')
    os.environ['AFL_COVERAGE_TYPE'] = 'NO_COLLISION'
    os.environ['AFL_CONVERT_COMPARISON_TYPE'] = 'ALL'
    os.environ['AFL_DICT_TYPE'] = 'OPTIMIZED'
    bin3_cmd = "{compiler} {flags} {target}.bc -o {target}-no-collision-all-opt {ldflags}".format(compiler='/afl/aflc-clang-fast++', flags=cppflags, target=fuzz_target, ldflags=ldflags)
    if os.system(bin3_cmd) != 0:
        raise ValueError("command '{command}' failed".format(command=bin3_cmd))

    print('[post_build] Copying afl-fuzz to $OUT directory')
    # Copy out the afl-fuzz binary as a build artifact.
    shutil.copy('/afl/afl-fuzz', os.environ['OUT'])

def build():
    """Build benchmark."""
    prepare_build_environment()

    utils.build_benchmark()

    print('[post_build] Extracting .bc file')
    fuzz_targets = get_fuzz_targets()
    for fuzz_target in fuzz_targets:
        post_build(fuzz_target)


def run_fuzz(input_corpus,
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

    # Note: dictionary automatically added by run_fuzz().

    # Use a dictionary for original afl as well.
    print('[run_fuzzer] Running AFL for original binary')
    src_file = "{target}-normalized-none-nopt.dict".format(target=target_binary)
    dst_file = "{target}-original.dict".format(target=target_binary)
    shutil.copy(src_file, dst_file)
    # Instead of generating a new dict, just hack this one 
    # to be non-optimized to prevent AFL from aborting.
    os.system("sed -i 's/OPTIMIZED/NORMAL/g' {dict}".format(dict=dst_file))
    afl_fuzz_thread1 = threading.Thread(target=run_fuzz,
                                        args=(input_corpus, output_corpus,
                                              "{target}-original".format(target=target_binary), 
                                              ['-S', 'slave-original']))
    afl_fuzz_thread1.start()

    print('[run_fuzzer] Running AFL for normalized and optimized dictionary')
    afl_fuzz_thread2 = threading.Thread(target=run_fuzz,
                                        args=(input_corpus, output_corpus,
                                              "{target}-normalized-none-nopt".format(target=target_binary), 
                                              ['-S', 'slave-normalized-nopt']))
    afl_fuzz_thread2.start()

    print('[run_fuzzer] Running AFL for FBSP and optimized dictionary')
    run_fuzz(input_corpus,
             output_corpus,
             "{target}-no-collision-all-opt".format(target=target_binary), 
             ['-S', 'slave-no-collision-all-opt'],
             hide_output=False)
