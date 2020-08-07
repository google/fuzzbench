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

from fuzzers import utils
LIB_BC_DIR = 'lib-bc'
SYMBOLIC_BUFFER = 'KleeInputBuf'
MODEL_VERSION = 'model_version'


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
    ldd_cmd = ['/usr/bin/ldd', '{target}'.format(target=fuzz_target)]
    output = ''
    try:
        output = subprocess.check_output(ldd_cmd, universal_newlines=True)
    except subprocess.CalledProcessError:
        raise ValueError('ldd failed')

    for line in output.split('\n'):
        if '=>' not in line:
            continue

        out_dir = '{out}/{lib_bc_dir}'.format(out=os.environ['OUT'],
                                              lib_bc_dir=LIB_BC_DIR)
        path = pathlib.Path(out_dir)
        path.mkdir(exist_ok=True)
        so_path = line.split('=>')[1].split(' ')[1]
        so_name = so_path.split('/')[-1].split('.')[0]
        if so_name:
            getbc_cmd = 'extract-bc -o {out_dir}/{so_name}.bc {target}'.format(
                target=so_path, out_dir=out_dir, so_name=so_name)
            print('[extract-bc command] | {getbc_cmd}'.format(
                getbc_cmd=getbc_cmd))
            # This will fail for most of the dependencies, which is fine. We
            # want to grab the .bc files for dependencies built in any given
            # benchmark's build.sh file.
            success = os.system(getbc_cmd)
            if success == 1:
                print('Got a bc file for {target}'.format(target=so_path))


def get_bc_files():
    """Returns list of .bc files in the OUT directory"""
    out_dir = './' + LIB_BC_DIR
    files = os.listdir(out_dir)
    bc_files = []
    for filename in files:
        if filename.split('.')[-1] == 'bc' and 'fuzz-target' not in filename:
            bc_files.append(filename)

    return bc_files


def get_fuzz_target():
    """Get the fuzz target name"""
    # For non oss-projects, FUZZ_TARGET contain the target binary.
    fuzz_target = os.getenv('FUZZ_TARGET', None)
    if fuzz_target is not None:
        return [fuzz_target]

    print('[get_fuzz_target] FUZZ_TARGET is not defined')

    # For these benchmarks, only return one file.
    targets = {
        'curl': 'curl_fuzzer_http',
        'openssl': 'x509',
        'systemd': 'fuzz-link-parser',
        'php': 'php-fuzz-parser'
    }

    for target, fuzzname in targets.items():
        if is_benchmark(target):
            return [os.path.join(os.environ['OUT'], fuzzname)]

    # For the reamining oss-projects, use some heuristics.
    # We look for binaries in the OUT directory and take it as our targets.
    # Note that we may return multiple binaries: this is necessary because
    # sometimes multiple binaries are generated and we don't know which will
    # be used for fuzzing (e.g., zlib benchmark).
    # dictionary above.
    out_dir = os.environ['OUT']
    files = os.listdir(out_dir)
    fuzz_targets = []
    for filename in files:
        candidate_bin = os.path.join(out_dir, filename)
        if 'fuzz' in filename and os.access(candidate_bin, os.X_OK):
            fuzz_targets += [candidate_bin]

    if len(fuzz_targets) == 0:
        raise ValueError("Cannot find binary")
    print("[get_fuzz_target] targets: %s" % fuzz_targets)
    return fuzz_targets


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

    fuzz_targets = get_fuzz_target()
    for target in fuzz_targets:
        getbc_cmd = 'extract-bc {target}'.format(target=target)

    if os.system(getbc_cmd) != 0:
        raise ValueError('extract-bc failed')
    for target in fuzz_targets:
        get_bcs_for_shared_libs(target)


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
    print('[run_cmd] {}'.format(cmd))

    output_stream = subprocess.DEVNULL if hide_output else None
    if ulimit_cmd:
        ulimit_command = [ulimit_cmd + ';']
        ulimit_command.extend(command)
        print('[ulimit_command] {}'.format(' '.join(ulimit_command)))
        ret = subprocess.call(' '.join(ulimit_command),
                              stdout=output_stream,
                              stderr=output_stream,
                              shell=True)
    else:
        ret = subprocess.call(command,
                              stdout=output_stream,
                              stderr=output_stream)
    if ret != 0:
        raise ValueError('command failed: {ret} - {cmd}'.format(ret=ret,
                                                                cmd=cmd))


def covert_seed_inputs(ktest_tool, input_klee, input_corpus):
    """
    Covert seeds to a format KLEE understands.

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
            print('[run_fuzzer] Truncating {path} ({file_size}) to \
                    {benchmark_size}'.format(path=seedfile,
                                             file_size=file_size,
                                             benchmark_size=benchmark_size))
            os.truncate(seedfile, benchmark_size)

        seed_in = '{seed}.ktest'.format(seed=seedfile)
        seed_out = os.path.join(input_klee, os.path.basename(seed_in))

        # Create file for symblic buffer
        input_file = '{seed}.ktest.{symbolic}'.format(seed=seedfile,
                                                      symbolic=SYMBOLIC_BUFFER)
        output_kfile = '{seed}.ktest'.format(seed=seedfile)
        shutil.copyfile(seedfile, input_file)
        os.rename(seedfile, input_file)

        # Create file for mode version
        model_input_file = '{seed}.ktest.{symbolic}'.format(
            seed=seedfile, symbolic=MODEL_VERSION)
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

    print('[run_fuzzer] Converted {converted} seed files'.format(
        converted=n_converted))

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
    file_in = '{file}.{symbuf}'.format(file=kfile, symbuf=SYMBOLIC_BUFFER)
    file_out = os.path.join(queue_dir, os.path.basename(ktest_fn))
    os.rename(file_in, file_out)

    # Check if this is a crash
    crash_regex = os.path.join(output_klee, '{fn}.*.err'.format(fn=ktest_fn))
    crashes = glob.glob(crash_regex)
    n_crashes = 0
    if len(crashes) == 1:
        crash_out = os.path.join(crash_dir, os.path.basename(ktest_fn))
        shutil.copy(file_out, crash_out)
        info_in = crashes[0]
        info_out = os.path.join(info_dir, os.path.basename(info_in))
        shutil.copy(info_in, info_out)
    return n_crashes


def convert_ktests(ktest_tool, output_klee, crash_dir, queue_dir, info_dir):
    """
    Convert KLEE output to binary seeds. Return the number of crashes
    """

    # Convert the output .ktest to binary format
    print('[run_fuzzer] Converting output files...')

    n_converted = 0
    n_crashes = 0

    files = glob.glob(os.path.join(output_klee, '*.ktest'))
    for kfile in files:
        n_crashes += convert_individual_ktest(ktest_tool, kfile, queue_dir,
                                              output_klee, crash_dir, info_dir)
        n_converted += 1

    print('[run_fuzzer] Converted {converted} output files'.format(
        converted=n_converted))

    return n_crashes


def fuzz(input_corpus, output_corpus, target_binary):
    """Run fuzzer."""

    # Set ulimit. Note: must be changed as this does not take effect
    if os.system('ulimit -s unlimited') != 0:
        raise ValueError('ulimit failed')

    # Convert corpus files to KLEE .ktest format
    out_dir = os.path.dirname(target_binary)
    ktest_tool = os.path.join(out_dir, 'bin/ktest-tool')
    output_klee = os.path.join(out_dir, 'output_klee')
    crash_dir = os.path.join(output_corpus, 'crashes')
    input_klee = os.path.join(out_dir, 'seeds_klee')
    queue_dir = os.path.join(output_corpus, 'queue')
    info_dir = os.path.join(output_corpus, 'info')
    emptydir(crash_dir)
    emptydir(queue_dir)
    emptydir(info_dir)
    emptydir(input_klee)
    rmdir(output_klee)

    n_converted = covert_seed_inputs(ktest_tool, input_klee, input_corpus)
    # Run KLEE
    # Option -only-output-states-covering-new makes
    # dumping ktest files faster.
    # New coverage means a new edge.
    # See lib/Core/StatsTracker.cpp:markBranchVisited()

    print('[run_fuzzer] Running target with klee')

    klee_bin = os.path.join(out_dir, 'bin/klee')
    target_binary_bc = '{}.bc'.format(target_binary)
    seconds = int(int(os.getenv('MAX_TOTAL_TIME', str(246060))) * 4 / 5)

    seeds_option = ['-zero-seed-extension', '-seed-dir', input_klee
                   ] if n_converted > 0 else []

    llvm_link_libs = []
    for filename in get_bc_files():
        llvm_link_libs.append('-link-llvm-lib=./{lib_bc}/{filename}'.format(
            lib_bc=LIB_BC_DIR, filename=filename))

    klee_cmd = [
        klee_bin,
        '-max-solver-time',
        '30s',
        '-log-timed-out-queries',
        '--max-time',
        '{}s'.format(seconds),
        '-libc',
        'uclibc',
        '-libcxx',
        '-posix-runtime',
        '--disable-verify',  # Needed because debug builds don't always work.
        '-output-dir',
        output_klee,
    ]

    klee_cmd.extend(llvm_link_libs)

    if seeds_option:
        klee_cmd.extend(seeds_option)

    size = get_size_for_benchmark()
    klee_cmd += [target_binary_bc, str(size)]
    run(klee_cmd, ulimit_cmd='ulimit -s unlimited')

    n_crashes = convert_ktests(ktest_tool, output_klee, crash_dir, queue_dir,
                               info_dir)

    print('[run_fuzzer] Found {crashed} crash files'.format(crashed=n_crashes))

    # For sanity check, we write a file to ensure
    # KLEE was able to terminate and convert all files
    done_file = os.path.join(output_corpus, 'DONE')
    with open(done_file, 'w') as file:
        file.write('Converted: {converted}\nBugs: {bugs}'.format(
            converted=n_converted, bugs=n_crashes))
