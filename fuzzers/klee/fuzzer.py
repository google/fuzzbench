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
# pylint: disable=too-many-arguments

import shutil
import os
import glob
import pathlib
import struct
import subprocess
import threading
import time
from datetime import datetime

from fuzzers import utils

LIB_BC_DIR = 'lib-bc'
SYMBOLIC_BUFFER = 'kleeInputBuf'
MODEL_VERSION = 'model_version'

MAX_SOLVER_TIME_SECONDS = 30
MAX_TOTAL_TIME_DEFAULT = 82800  # Default experiment duration = 23 hrs.


def is_benchmark(name):
    """Check if the benchmark contains the string |name|"""
    benchmark = os.getenv('BENCHMARK', None)
    return benchmark is not None and name in benchmark


def prepare_build_environment():
    """Set environment variables used to build benchmark."""
    if is_benchmark('sqlite3'):
        sqlite3_flags = [
            '-DSQLITE_THREADSAFE=0', '-DSQLITE_OMIT_LOAD_EXTENSION',
            '-DSQLITE_DEFAULT_MEMSTATUS=0', '-DSQLITE_MAX_EXPR_DEPTH=0',
            '-DSQLITE_OMIT_DECLTYPE', '-DSQLITE_OMIT_DEPRECATED',
            '-DSQLITE_DEFAULT_PAGE_SIZE=512', '-DSQLITE_DEFAULT_CACHE_SIZE=10',
            '-DSQLITE_DISABLE_INTRINSIC', '-DSQLITE_DISABLE_LFS',
            '-DYYSTACKDEPTH=20', '-DSQLITE_OMIT_LOOKASIDE', '-DSQLITE_OMIT_WAL',
            '-DSQLITE_DEFAULT_LOOKASIDE=\'64,5\'',
            '-DSQLITE_OMIT_PROGRESS_CALLBACK', '-DSQLITE_OMIT_SHARED_CACHE'
        ]
        utils.append_flags('CFLAGS', sqlite3_flags)
        utils.append_flags('CXXFLAGS', sqlite3_flags)
        #This convinces sqlite3 ./configure script to not reenable threads
        os.environ['enable_threadsafe'] = 'no'

    # See https://klee.github.io/tutorials/testing-function/
    cflags = ['-O0', '-Xclang', '-disable-O0-optnone']
    utils.append_flags('CFLAGS', cflags)
    utils.append_flags('CXXFLAGS', cflags)

    # Add flags for various benchmarks.
    add_compilation_cflags()

    os.environ['LLVM_CC_NAME'] = 'clang-6.0'
    os.environ['LLVM_CXX_NAME'] = 'clang++-6.0'
    os.environ['LLVM_AR_NAME'] = 'llvm-ar-6.0'
    os.environ['LLVM_LINK_NAME'] = 'llvm-link-6.0'
    os.environ['LLVM_COMPILER'] = 'clang'
    os.environ['CC'] = 'wllvm'
    os.environ['CXX'] = 'wllvm++'

    os.environ['FUZZER_LIB'] = '/libAFL.a'  # -L/ -lKleeMock -lpthread'

    # Fix FUZZER_LIB for various benchmarks.
    fix_fuzzer_lib()


def openthread_suppress_error_flags():
    """Suppress errors for openthread"""
    return [
        '-Wno-error=embedded-directive',
        '-Wno-error=gnu-zero-variadic-macro-arguments',
        '-Wno-error=overlength-strings', '-Wno-error=c++11-long-long',
        '-Wno-error=c++11-extensions', '-Wno-error=variadic-macros'
    ]


def get_size_for_benchmark():
    """
    Returns the size for the seed for each benchmark.
    """
    size = 256
    if 're2-2014-12-09' in os.environ['BENCHMARK']:
        size = 64
    if 'libpng' in os.environ['BENCHMARK']:
        size = 128
    return size


def get_bcs_for_shared_libs(fuzz_target):
    """Get shared libs paths for the fuzz_target"""
    ldd_cmd = ['/usr/bin/ldd', f'{fuzz_target}']
    output = ''
    try:
        output = subprocess.check_output(ldd_cmd, universal_newlines=True)
    except subprocess.CalledProcessError as error:
        raise ValueError('ldd failed') from error

    for line in output.split('\n'):
        if '=>' not in line:
            continue

        out_dir = f'{os.environ["OUT"]}/{LIB_BC_DIR}'
        path = pathlib.Path(out_dir)
        path.mkdir(exist_ok=True)
        so_path = line.split('=>')[1].split(' ')[1]
        so_name = so_path.split('/')[-1].split('.')[0]
        if so_name:
            getbc_cmd = f'extract-bc -o {out_dir}/{so_name}.bc {so_path}'
            print(f'[extract-bc command] | {getbc_cmd}')
            # This will fail for most of the dependencies, which is fine. We
            # want to grab the .bc files for dependencies built in any given
            # benchmark's build.sh file.
            success = os.system(getbc_cmd)
            if success == 1:
                print(f'Got a bc file for {so_path}')


def get_bc_files():
    """Returns list of .bc files in the OUT directory"""
    out_dir = './' + LIB_BC_DIR
    files = os.listdir(out_dir)
    bc_files = []
    for filename in files:
        if filename.split('.')[-1] == 'bc' and 'fuzz-target' not in filename:
            bc_files.append(filename)

    return bc_files


def fix_fuzzer_lib():
    """Fix FUZZER_LIB for certain benchmarks"""

    os.environ['FUZZER_LIB'] += ' -L/ -lKleeMock -lpthread'

    if is_benchmark('curl'):
        shutil.copy('/libKleeMock.so', '/usr/lib/libKleeMock.so')

    shutil.copy('/libAFL.a', '/usr/lib/libFuzzingEngine.a')
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


def build():
    """Build benchmark."""
    prepare_build_environment()

    utils.build_benchmark()

    fuzz_target = os.getenv('FUZZ_TARGET')
    fuzz_target_path = os.path.join(os.environ['OUT'], fuzz_target)
    getbc_cmd = f'extract-bc {fuzz_target_path}'
    if os.system(getbc_cmd) != 0:
        raise ValueError('extract-bc failed')
    get_bcs_for_shared_libs(fuzz_target_path)


def rmdir(path):
    """"Remove a directory recursively"""
    if os.path.isdir(path):
        shutil.rmtree(path)


def emptydir(path):
    """Empty a directory"""
    rmdir(path)

    os.mkdir(path)


# pylint: disable=too-many-locals
def run(command, hide_output=False, ulimit_cmd=None):
    """Run the command |command|, optionally, run |ulimit_cmd| first."""
    cmd = ' '.join(command)
    print(f'[run_cmd] {cmd}')

    output_stream = subprocess.DEVNULL if hide_output else None
    if ulimit_cmd:
        ulimit_command = [ulimit_cmd + ';']
        ulimit_command.extend(command)
        print(f'[ulimit_command] {" ".join(ulimit_command)}')
        ret = subprocess.call(' '.join(ulimit_command),
                              stdout=output_stream,
                              stderr=output_stream,
                              shell=True)
    else:
        ret = subprocess.call(command,
                              stdout=output_stream,
                              stderr=output_stream)
    if ret != 0:
        raise ValueError(f'command failed: {ret} - {cmd}')


def convert_seed_inputs(ktest_tool, input_klee, input_corpus):
    """
    Convert seeds to a format KLEE understands.

    Returns the number of converted seeds.
    """

    print('[run_fuzzer] Converting seed files...')

    # We put the file data into the symbolic buffer,
    # and the model_version set to 1 for uc-libc
    model = struct.pack('@i', 1)
    files = glob.glob(os.path.join(input_corpus, '*'))
    n_converted = 0

    for seedfile in files:
        if '.ktest' in seedfile:
            continue

        if not os.path.isfile(seedfile):
            continue

        # Truncate the seed to the max size for the benchmark
        file_size = os.path.getsize(seedfile)
        benchmark_size = get_size_for_benchmark()
        if file_size > benchmark_size:
            print(f'[run_fuzzer] Truncating {seedfile} ({file_size}) to '
                  f'{benchmark_size}')
            os.truncate(seedfile, benchmark_size)

        seed_in = f'{seedfile}.ktest'
        seed_out = os.path.join(input_klee, os.path.basename(seed_in))

        # Create file for symblic buffer
        input_file = f'{seedfile}.ktest.{SYMBOLIC_BUFFER}'
        output_kfile = f'{seedfile}.ktest'
        shutil.copyfile(seedfile, input_file)
        os.rename(seedfile, input_file)

        # Create file for mode version
        model_input_file = f'{seedfile}.ktest.{MODEL_VERSION}'
        with open(model_input_file, 'wb') as mfile:
            mfile.write(model)

        # Run conversion tool
        convert_cmd = [
            ktest_tool, 'create', output_kfile, '--args', seed_out, '--objects',
            MODEL_VERSION, SYMBOLIC_BUFFER
        ]

        run(convert_cmd)

        # Move the resulting file to klee corpus dir
        os.rename(seed_in, seed_out)

        n_converted += 1

    print(f'[run_fuzzer] Converted {n_converted} seed files')

    return n_converted


# pylint: disable=wrong-import-position
# pylint: disable=too-many-locals
def convert_individual_ktest(ktest_tool, kfile, queue_dir, output_klee,
                             crash_dir, info_dir):
    """
    Convert an individual ktest, return the number of crashes.
    """
    convert_cmd = [ktest_tool, 'extract', kfile, '--objects', SYMBOLIC_BUFFER]

    run(convert_cmd)

    # And copy the resulting file in output_corpus
    ktest_fn = os.path.splitext(kfile)[0]
    file_in = f'{kfile}.{SYMBOLIC_BUFFER}'
    file_out = os.path.join(queue_dir, os.path.basename(ktest_fn))
    os.rename(file_in, file_out)

    # Check if this is a crash
    crash_regex = os.path.join(output_klee, f'{ktest_fn}.*.err')
    crashes = glob.glob(crash_regex)
    n_crashes = 0
    if len(crashes) == 1:
        crash_out = os.path.join(crash_dir, os.path.basename(ktest_fn))
        shutil.copy(file_out, crash_out)
        info_in = crashes[0]
        info_out = os.path.join(info_dir, os.path.basename(info_in))
        shutil.copy(info_in, info_out)
    return n_crashes


# pylint: disable=import-error
# pylint: disable=import-outside-toplevel
def monitor_resource_usage():
    """Monitor resource consumption."""

    import psutil
    print('[resource_thread] Starting resource usage monitoring...')

    start = datetime.now()
    while True:
        time.sleep(60 * 5)
        message = (f'{psutil.cpu_times_percent(percpu=False)}\n'
                   f'{psutil.virtual_memory()}\n'
                   f'{psutil.swap_memory()}')
        now = datetime.now()
        print(
            f'[resource_thread] Resource usage after {now - start}:\n{message}')


# pylint: disable=import-error
# pylint: disable=import-outside-toplevel
def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""

    import psutil

    # Set ulimit. Note: must be changed as this does not take effect
    if os.system('ulimit -s unlimited') != 0:
        raise ValueError('ulimit failed')

    # Convert corpus files to KLEE .ktest format
    out_dir = os.path.dirname(target_binary)
    ktest_tool = os.path.join(out_dir, 'bin/ktest-tool')
    crash_dir = os.path.join(output_corpus, 'crashes')
    input_klee = os.path.join(out_dir, 'seeds_klee')
    queue_dir = os.path.join(output_corpus, 'queue')
    info_dir = os.path.join(output_corpus, 'info')
    emptydir(crash_dir)
    emptydir(info_dir)
    emptydir(input_klee)
    rmdir(queue_dir)

    n_converted = convert_seed_inputs(ktest_tool, input_klee, input_corpus)
    # Run KLEE
    # Option -only-output-states-covering-new makes
    # dumping ktest files faster.
    # See lib/Core/StatsTracker.cpp:markBranchVisited()

    print('[run_fuzzer] Starting resource monitoring thread')
    monitoring_thread = threading.Thread(target=monitor_resource_usage)
    monitoring_thread.start()

    print('[run_fuzzer] Running target with klee')

    klee_bin = os.path.join(out_dir, 'bin/klee')
    target_binary_bc = f'{target_binary}.bc'
    max_time_seconds = (
        int(os.getenv('MAX_TOTAL_TIME', str(MAX_TOTAL_TIME_DEFAULT))) * 4) // 5

    seeds_option = ['-zero-seed-extension', '-seed-dir', input_klee
                   ] if n_converted > 0 else []

    llvm_link_libs = []
    for filename in get_bc_files():
        llvm_link_libs.append(f'-link-llvm-lib=./{LIB_BC_DIR}/{filename}')

    max_memory_mb = str(int(psutil.virtual_memory().available // 10**6 * 0.9))

    klee_cmd = [
        klee_bin,
        '-ignore-solver-failures',
        '-always-output-seeds',
        '-output-format-binary',
        '-output-symbolic-name',
        f'{SYMBOLIC_BUFFER}',
        '-max-memory',
        max_memory_mb,
        '-max-solver-time',
        f'{MAX_SOLVER_TIME_SECONDS}s',
        '-log-timed-out-queries',
        '-max-time',
        f'{max_time_seconds}s',
        '-libc',
        'uclibc',
        '-libcxx',
        '-posix-runtime',
        '-disable-verify',  # Needed because debug builds don't always work.
        '-output-dir',
        queue_dir,
    ]

    klee_cmd.extend(llvm_link_libs)

    if seeds_option:
        klee_cmd.extend(seeds_option)

    size = get_size_for_benchmark()
    klee_cmd += [target_binary_bc, str(size)]
    run(klee_cmd, ulimit_cmd='ulimit -s unlimited')

    # Klee has now terminated.
    print('[run_fuzzer] Klee has terminated.')
