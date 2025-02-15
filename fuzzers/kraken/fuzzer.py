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

import os, subprocess
import shutil

from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers import utils

def check_skip_det_compatible(additional_flags):
    """ Checks if additional flags are compatible with '-d' option"""
    # AFL refuses to take in '-d' with '-M' or '-S' options for parallel mode.
    # (cf. https://github.com/google/AFL/blob/8da80951/afl-fuzz.c#L7477)
    if '-M' in additional_flags or '-S' in additional_flags:
        return False
    return True

def run_afl_fuzz(input_corpus,
                 output_corpus,
                 target_binary,
                 additional_flags=None,
                 hide_output=False,
                 timeout=None,
                 env=None):
    """Run afl-fuzz."""
    # Spawn the afl fuzzing process.
    print('[run_afl_fuzz] Running target with afl-fuzz')
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
        '1000+',  # Use same default 1 sec timeout, but add '+' to skip hangs.
    ]
    # Use '-d' to skip deterministic mode, as long as it it compatible with
    # additional flags.
    if not additional_flags or check_skip_det_compatible(additional_flags):
        command.append('-z')
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
    if timeout:
        command = ['timeout', '--signal=SIGINT', '--kill-after=120s', '--preserve-status', str(timeout)] + command
    print('[run_afl_fuzz] Running command: ' + ' '.join(command))
    output_stream = subprocess.DEVNULL if hide_output else None
    return subprocess.Popen(command, stdout=output_stream, stderr=output_stream, env=env)


def get_cmplog_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'cmplog')


def get_uninstrumented_build_directory(target_directory):
    """Return path to CmpLog target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build_aflpp(*args):  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    # BUILD_MODES is not already supported by fuzzbench, meanwhile we provide
    # a default configuration.

    env1 = os.environ.copy()
    env1['PATH'] = '/usr/local/bin:' + env1['PATH']
    build_modes = list(args)
    if 'BUILD_MODES' in env1:
        build_modes = env1['BUILD_MODES'].split(',')

    # Placeholder comment.
    build_directory = env1['OUT']

    # If nothing was set this is the default:
    if not build_modes:
        build_modes = ['tracepc', 'cmplog', 'dict2file']

    # For bug type benchmarks we have to instrument via native clang pcguard :(
    build_flags = env1['CFLAGS']

    if build_flags.find(
            'array-bounds'
    ) != -1 and 'qemu' not in build_modes and 'classic' not in build_modes:
        if 'gcc' not in build_modes:
            build_modes[0] = 'native'

    # Instrumentation coverage modes:
    if 'lto' in build_modes:
        env1['CC'] = '/afl/afl-clang-lto'
        env1['CXX'] = '/afl/afl-clang-lto++'
        edge_file = build_directory + '/aflpp_edges.txt'
        env1['AFL_LLVM_DOCUMENT_IDS'] = edge_file
        if os.path.isfile('/usr/local/bin/llvm-ranlib-13'):
            env1['RANLIB'] = 'llvm-ranlib-13'
            env1['AR'] = 'llvm-ar-13'
            env1['AS'] = 'llvm-as-13'
        elif os.path.isfile('/usr/local/bin/llvm-ranlib-12'):
            env1['RANLIB'] = 'llvm-ranlib-12'
            env1['AR'] = 'llvm-ar-12'
            env1['AS'] = 'llvm-as-12'
        else:
            env1['RANLIB'] = 'llvm-ranlib'
            env1['AR'] = 'llvm-ar'
            env1['AS'] = 'llvm-as'
    elif 'qemu' in build_modes:
        env1['CC'] = 'clang'
        env1['CXX'] = 'clang++'
    elif 'gcc' in build_modes:
        env1['CC'] = 'afl-gcc-fast'
        env1['CXX'] = 'afl-g++-fast'
        if build_flags.find('array-bounds') != -1:
            env1['CFLAGS'] = '-fsanitize=address -O1'
            env1['CXXFLAGS'] = '-fsanitize=address -O1'
        else:
            env1['CFLAGS'] = ''
            env1['CXXFLAGS'] = ''
            env1['CPPFLAGS'] = ''
    else:
        env1['CC'] = '/afl/afl-clang-fast'
        env1['CXX'] = '/afl/afl-clang-fast++'

    print('AFL++ build: ')
    print(build_modes)

    if 'qemu' in build_modes or 'symcc' in build_modes:
        env1['CFLAGS'] = ' '.join(utils.NO_SANITIZER_COMPAT_CFLAGS)
        cxxflags = [utils.LIBCPLUSPLUS_FLAG] + utils.NO_SANITIZER_COMPAT_CFLAGS
        env1['CXXFLAGS'] = ' '.join(cxxflags)

    if 'tracepc' in build_modes or 'pcguard' in build_modes:
        env1['AFL_LLVM_USE_TRACE_PC'] = '1'
    elif 'classic' in build_modes:
        env1['AFL_LLVM_INSTRUMENT'] = 'CLASSIC'
    elif 'native' in build_modes:
        env1['AFL_LLVM_INSTRUMENT'] = 'LLVMNATIVE'

    # Instrumentation coverage options:
    # Do not use a fixed map location (LTO only)
    if 'dynamic' in build_modes:
        env1['AFL_LLVM_MAP_DYNAMIC'] = '1'
    # Use a fixed map location (LTO only)
    if 'fixed' in build_modes:
        env1['AFL_LLVM_MAP_ADDR'] = '0x10000'
    # Generate an extra dictionary.
    if 'dict2file' in build_modes or 'native' in build_modes:
        env1['AFL_LLVM_DICT2FILE'] = build_directory + '/afl++.dict'
        env1['AFL_LLVM_DICT2FILE_NO_MAIN'] = '1'
    # Enable context sentitivity for LLVM mode (non LTO only)
    if 'ctx' in build_modes:
        env1['AFL_LLVM_CTX'] = '1'
    # Enable N-gram coverage for LLVM mode (non LTO only)
    if 'ngram2' in build_modes:
        env1['AFL_LLVM_NGRAM_SIZE'] = '2'
    elif 'ngram3' in build_modes:
        env1['AFL_LLVM_NGRAM_SIZE'] = '3'
    elif 'ngram4' in build_modes:
        env1['AFL_LLVM_NGRAM_SIZE'] = '4'
    elif 'ngram5' in build_modes:
        env1['AFL_LLVM_NGRAM_SIZE'] = '5'
    elif 'ngram6' in build_modes:
        env1['AFL_LLVM_NGRAM_SIZE'] = '6'
    elif 'ngram7' in build_modes:
        env1['AFL_LLVM_NGRAM_SIZE'] = '7'
    elif 'ngram8' in build_modes:
        env1['AFL_LLVM_NGRAM_SIZE'] = '8'
    elif 'ngram16' in build_modes:
        env1['AFL_LLVM_NGRAM_SIZE'] = '16'
    if 'ctx1' in build_modes:
        env1['AFL_LLVM_CTX_K'] = '1'
    elif 'ctx2' in build_modes:
        env1['AFL_LLVM_CTX_K'] = '2'
    elif 'ctx3' in build_modes:
        env1['AFL_LLVM_CTX_K'] = '3'
    elif 'ctx4' in build_modes:
        env1['AFL_LLVM_CTX_K'] = '4'

    # Only one of the following OR cmplog
    # enable laf-intel compare splitting
    if 'laf' in build_modes:
        env1['AFL_LLVM_LAF_SPLIT_SWITCHES'] = '1'
        env1['AFL_LLVM_LAF_SPLIT_COMPARES'] = '1'
        env1['AFL_LLVM_LAF_SPLIT_FLOATS'] = '1'
        if 'autodict' not in build_modes:
            env1['AFL_LLVM_LAF_TRANSFORM_COMPARES'] = '1'

    if 'eclipser' in build_modes:
        env1['FUZZER_LIB'] = '/libStandaloneFuzzTarget.a'
    else:
        env1['FUZZER_LIB'] = '/libAFLDriver.a'

    # Some benchmarks like lcms. (see:
    # https://github.com/mm2/Little-CMS/commit/ab1093539b4287c233aca6a3cf53b234faceb792#diff-f0e6d05e72548974e852e8e55dffc4ccR212)
    # fail to compile if the compiler outputs things to stderr in unexpected
    # cases. Prevent these failures by using AFL_QUIET to stop afl-clang-fast
    # from writing AFL specific messages to stderr.
    env1['AFL_QUIET'] = '1'
    env1['AFL_MAP_SIZE'] = '2621440'

    src = os.getenv('SRC')
    work = os.getenv('WORK')

    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark(env=env1)

    if 'cmplog' in build_modes and 'qemu' not in build_modes:

        # CmpLog requires an build with different instrumentation.
        new_env = env1.copy()
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
        with utils.restore_directory(src), utils.restore_directory(work):
            utils.build_benchmark(env=new_env)

    if 'symcc' in build_modes:

        symcc_build_directory = get_uninstrumented_build_directory(
            build_directory)
        os.mkdir(symcc_build_directory)

        # symcc requires an build with different instrumentation.
        new_env = env1.copy()
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
        with utils.restore_directory(src), utils.restore_directory(work):
            utils.build_benchmark(env=new_env)

    shutil.copy('/afl/afl-fuzz', build_directory)
    shutil.copy('/afl/afl-showmap', build_directory)
    shutil.copy('/afl/afl-cmin', build_directory)
    if os.path.exists('/afl/afl-qemu-trace'):
        shutil.copy('/afl/afl-qemu-trace', build_directory)
    if os.path.exists('/aflpp_qemu_driver_hook.so'):
        shutil.copy('/aflpp_qemu_driver_hook.so', build_directory)
    if os.path.exists('/get_frida_entry.sh'):
        shutil.copy('/afl/afl-frida-trace.so', build_directory)
        shutil.copy('/get_frida_entry.sh', build_directory)


# pylint: disable=too-many-arguments
def fuzz_aflpp(input_corpus,
         output_corpus,
         target_binary,
         flags=tuple(),
         skip=False,
         no_cmplog=False,
         timeout=None,
         skip_calibration=False):  # pylint: disable=too-many-arguments
    """Run fuzzer."""
    env1 = os.environ.copy()
    if skip_calibration:
        env1['AFL_NO_STARTUP_CALIBRATION'] = '1'
    # Calculate CmpLog binary path from the instrumented target binary.
    target_binary_directory = os.path.dirname(target_binary)
    cmplog_target_binary_directory = (
        get_cmplog_build_directory(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    cmplog_target_binary = os.path.join(cmplog_target_binary_directory,
                                        target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    # decomment this to enable libdislocator.
    # env1['AFL_ALIGNED_ALLOC'] = '1' # align malloc to max_align_t
    # env1['AFL_PRELOAD'] = '/afl/libdislocator.so'

    flags = list(flags)

    if os.path.exists('./afl++.dict'):
        flags += ['-x', './afl++.dict']

    # Move the following to skip for upcoming _double tests:
    if os.path.exists(cmplog_target_binary) and no_cmplog is False:
        flags += ['-c', cmplog_target_binary]

    #env1['AFL_IGNORE_TIMEOUTS'] = '1'
    env1['AFL_IGNORE_UNKNOWN_ENVS'] = '1'
    env1['AFL_FAST_CAL'] = '1'
    env1['AFL_NO_WARN_INSTABILITY'] = '1'
    env1['AFL_NO_AFFINITY'] = '1'
    env1['AFL_NO_UI'] = '1'

    if not skip:
        env1['AFL_DISABLE_TRIM'] = '1'
        env1['AFL_CMPLOG_ONLY_NEW'] = '1'
        if 'ADDITIONAL_ARGS' in env1:
            flags += env1['ADDITIONAL_ARGS'].split(' ')

    return run_afl_fuzz(input_corpus,
                    output_corpus,
                    target_binary,
                    additional_flags=flags,
                    timeout=timeout,
                    env=env1)

# LibAFL integration code

def build_libafl():  # pylint: disable=too-many-branches,too-many-statements
    """Build benchmark."""
    env1 = os.environ.copy()
    env1['CC'] = ('/libafl/fuzzers/fuzzbench/fuzzbench'
                        '/target/release-fuzzbench/libafl_cc')
    env1['CXX'] = ('/libafl/fuzzers/fuzzbench/fuzzbench'
                         '/target/release-fuzzbench/libafl_cxx')

    env1['ASAN_OPTIONS'] = 'abort_on_error=0:allocator_may_return_null=1'
    env1['UBSAN_OPTIONS'] = 'abort_on_error=0'

    cflags = ['--libafl']
    cxxflags = ['--libafl', '--std=c++14']
    utils.append_flags('CFLAGS', cflags, env=env1)
    utils.append_flags('CXXFLAGS', cxxflags, env=env1)
    utils.append_flags('LDFLAGS', cflags, env=env1)

    env1['FUZZER_LIB'] = '/stub_rt.a'
    with utils.restore_directory(os.getenv('SRC')), utils.restore_directory(os.getenv('WORK')):
        utils.build_benchmark(env=env1)


def fuzz_libafl(input_corpus, output_corpus, target_binary, timeout=None):
    """Run fuzzer."""
    env1 = os.environ.copy()
    env1['ASAN_OPTIONS'] = 'abort_on_error=1:detect_leaks=0:'\
                                 'malloc_context_size=0:symbolize=0:'\
                                 'allocator_may_return_null=1:'\
                                 'detect_odr_violation=0:handle_segv=0:'\
                                 'handle_sigbus=0:handle_abort=0:'\
                                 'handle_sigfpe=0:handle_sigill=0'
    env1['UBSAN_OPTIONS'] =  'abort_on_error=1:'\
                                   'allocator_release_to_os_interval_ms=500:'\
                                   'handle_abort=0:handle_segv=0:'\
                                   'handle_sigbus=0:handle_sigfpe=0:'\
                                   'handle_sigill=0:print_stacktrace=0:'\
                                   'symbolize=0:symbolize_inline_frames=0'
    # Create at least one non-empty seed to start.
    utils.create_seed_file_for_empty_corpus(input_corpus)
    dictionary_path = utils.get_dictionary_path(target_binary)
    command = [target_binary]
    if dictionary_path:
        command += (['-x', dictionary_path])
    command += (['-o', output_corpus, '-i', input_corpus])
    fuzzer_env = env1.copy()
    fuzzer_env['LD_PRELOAD'] = '/usr/lib/x86_64-linux-gnu/libjemalloc.so.2'
    if timeout:
        # need to use SIGTERM to stop libafl
        command = ['timeout', '--signal=SIGTERM', '--kill-after=120s', '--preserve-status', str(timeout)] + command

    print(command)
    return subprocess.Popen(command, cwd=os.environ['OUT'], env=fuzzer_env)


def build():
    """Build benchmark."""
    os.makedirs('/out/libafl_out', exist_ok=True)
    os.environ['OUT'] = '/out/libafl_out'
    build_libafl()

    os.environ['OUT'] = '/out'
    build_aflpp()


def fuzz(input_corpus, output_corpus, target_binary, *args, **kwargs):
    """Run fuzzer."""
    
    INITIAL_FUZZING_TIME = 60 * 60 * 10 # 10 hours
    # INITIAL_FUZZING_TIME = 7
    INITIAL_FUZZING_TIME = str(INITIAL_FUZZING_TIME) + 's'
    
    SECOND_FUZZING_TIME = 60 * 60 * 9 # 9 hours
    SECOND_FUZZING_TIME = str(SECOND_FUZZING_TIME) + 's'

    # write a txt to corpus folder. TODO
    from datetime import datetime
    start = datetime.now()
    with open(os.path.join(output_corpus, 'README.txt'), 'w') as f:
        f.write('''Kraken is an ensemble fuzzer. So it stores seeds in three places:
- /out/corpus/all_corpus
- /out/corpus/aflpp_corpus
- /out/corpus/libafl_corpus''')

    aflpp_corpus_dir = os.path.join(output_corpus,'aflpp_corpus')
    os.makedirs(aflpp_corpus_dir, exist_ok=True)
    libafl_corpus_dir = os.path.join(output_corpus,'libafl_corpus')
    os.makedirs(libafl_corpus_dir, exist_ok=True)

    target_binary_name = os.path.basename(target_binary)
    aflpp_binary = os.path.join('/out', target_binary_name)
    libafl_binary = os.path.join('/out/libafl_out', target_binary_name)

    p1 = fuzz_aflpp(input_corpus, aflpp_corpus_dir, aflpp_binary, timeout=INITIAL_FUZZING_TIME, *args, **kwargs)
    p2 = fuzz_libafl(input_corpus, libafl_corpus_dir, libafl_binary, timeout=INITIAL_FUZZING_TIME, *args, **kwargs)
    p1.wait()
    p2.wait()
    
    print(datetime.now()-start)
    print("Starting corpus minimization...")
    cmin_collected_dir = os.path.join(output_corpus,'all_corpus')
    os.makedirs(cmin_collected_dir, exist_ok=True)
    # collect corpus to a single directory
    os.system('cp ' + aflpp_corpus_dir + '/default/queue/* ' + cmin_collected_dir)
    os.system('cp ' + aflpp_corpus_dir + '/default/crashes/* ' + cmin_collected_dir)
    os.system('cp ' + libafl_corpus_dir + '/queue/* ' + cmin_collected_dir)
    os.system('cp ' + libafl_corpus_dir + '/crashes/* ' + cmin_collected_dir)
    
    # run afl cmin
    shutil.rmtree(input_corpus, ignore_errors=True)
    os.makedirs(input_corpus, exist_ok=True)
    
    command = ['./afl-cmin', '-m', 'none', '-t', '1000+', '-i', cmin_collected_dir, '-o', input_corpus, '--', aflpp_binary, "@@"]
    print(" ".join(command))
    p = subprocess.Popen(command, cwd=os.environ['OUT'])
    p.wait()
    
    import time
    time.sleep(2)

    # clear all previous data
    shutil.rmtree(aflpp_corpus_dir, ignore_errors=True)
    os.makedirs(aflpp_corpus_dir, exist_ok=True)
    shutil.rmtree(libafl_corpus_dir, ignore_errors=True)
    os.makedirs(libafl_corpus_dir, exist_ok=True)

    additional_flags = ['-p', 'mmopt']

    # rerun two fuzzers.
    print(datetime.now()-start)
    print("Rerun two fuzzers...")
    p1 = fuzz_aflpp(input_corpus, aflpp_corpus_dir, aflpp_binary, flags=additional_flags, timeout=SECOND_FUZZING_TIME, skip_calibration=True, *args, **kwargs)
    p2 = fuzz_libafl(input_corpus, libafl_corpus_dir, libafl_binary, timeout=SECOND_FUZZING_TIME, *args, **kwargs)
    p1.wait()
    p2.wait()

    additional_flags = ['-p', 'rare']

    print(datetime.now()-start)
    print("Starting Fuzzing 3rd under different config...")
    p1 = fuzz_aflpp(input_corpus, aflpp_corpus_dir, aflpp_binary, flags=additional_flags, skip_calibration=True, *args, **kwargs)
    p2 = fuzz_libafl(input_corpus, libafl_corpus_dir, libafl_binary, *args, **kwargs)
    # wait infinately
    p1.wait()
    p2.wait()
