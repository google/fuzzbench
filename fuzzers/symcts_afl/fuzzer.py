# Copyright 2021 Google LLC
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
''' Uses the SymCC-AFL hybrid from SymCC. '''

import os
import time
import shutil
import threading
import subprocess
import shutil

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer
from fuzzers.aflplusplus import fuzzer as aflplusplus_fuzzer


def get_symcc_build_dir(target_directory):
    """Return path to uninstrumented target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build():
    """Build an AFL version and SymCC version of the benchmark"""
    print('Step 0: Building a vanilla version of the benchmark')
    new_env = os.environ.copy()
    new_env['OUT'] = "/out/vanilla"
    new_env['FUZZER_LIB'] = '/out/vanilla/afl_driver.o'
    utils.build_benchmark(env=new_env)

    shutil.rmtree("/out/cmplog")
    # print('Step 1: Building a cmplog version of the benchmark')
    # new_env = os.environ.copy()
    # new_env['OUT'] = "/out/cmplog"
    # new_env['FUZZER_LIB'] = '/out/cmplog/afl_driver.o'
    # new_env['AFL_LLVM_CMPLOG'] = '1'
    # new_env['CC'] = '/afl/afl-clang-fast'
    # new_env['CXX'] = '/afl/afl-clang-fast++'
    # utils.build_benchmark(env=new_env)

    print('Step 2: Building with AFL')
    build_directory = os.environ['OUT']

    # Save the environment for use in SymCC
    new_env = os.environ.copy()

    # First build with AFL.
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        aflplusplus_fuzzer.build('cmplog')

    # First build with AFL.
    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        aflplusplus_fuzzer.build('tracepc')

    print('Step 3: Completed AFL build')
    # Copy over AFL artifacts needed by SymCC.
    shutil.copy('/afl/afl-fuzz', build_directory)
    shutil.copy('/afl/afl-showmap', build_directory)

    # Build the SymCC-instrumented target.
    print('Step 4: Building the benchmark with SymCC')
    symcc_build_dir = get_symcc_build_dir(os.environ['OUT'])
    os.mkdir(symcc_build_dir)

    # Set flags to ensure compilation with SymCC.
    new_env['CC'] = '/symcc/build/symcc'
    new_env['CXX'] = '/symcc/build/sym++'
    new_env['CXXFLAGS'] = new_env['CXXFLAGS'].replace('-stlib=libc++', '')
    new_env['CXXFLAGS'] += ' -ldl -lm'
    # new_env['SYMCC_EXTRA_CFLAGS'] = '-l:libc_symcc_preload.a'
    # new_env['SYMCC_EXTRA_CXXFLAGS'] = '-l:libc_symcc_preload.a'
    new_env['SYMCC_EXTRA_CFLAGS'] = '-g'
    new_env['SYMCC_EXTRA_LDFLAGS'] = '-L /libs_symcc/ -l:libc_symcc_preload.a'
    new_env['FUZZER_LIB'] = '/libfuzzer-main.o'
    new_env['OUT'] = symcc_build_dir
    new_env['LIBRARY_PATH'] = new_env.get('LIBRARY_PATH', '') + ":/libs_symcc/:/libs/"

    new_env['CXXFLAGS'] += ' -fno-sanitize=all '
    new_env['CFLAGS'] += ' -fno-sanitize=all '
    new_env['SYMCC_RUNTIME_DIR'] = "/libs_symcc/" # SymCC should look for the runtime in the same directory so our copying works
    new_env['LD_LIBRARY_PATH'] = new_env.get('LD_LIBRARY_PATH', '') + ":/libs_symcc/:/libs/"


    # Setting this environment variable instructs SymCC to use the
    # libcxx library compiled with SymCC instrumentation.
    new_env['SYMCC_LIBCXX_PATH'] = '/libcxx_native_build'

    # Instructs SymCC to consider no symbolic inputs at runtime. This is needed
    # if, for example, some tests are run during compilation of the benchmark.
    new_env['SYMCC_NO_SYMBOLIC_INPUT'] = '1'
    new_env['SYMCC_DISABLE_WRITING'] = "1" # needed for the symcts runtime to run during tests (missing shmem env vars)

    # Build benchmark.
    utils.build_benchmark(env=new_env)

    print("COPYING A BUNCH OF STUFF IN ", symcc_build_dir)
    # Copy over symcc artifacts and symbolic libc++.
    shutil.copy(
        "/mctsse/implementation/libfuzzer_stb_image_symcts/runtime/target/release/libSymRuntime.so",
        symcc_build_dir)
    shutil.copy("/z3/lib/libz3.so", os.path.join(symcc_build_dir, "libz3.so"))
    # shutil.copy("/usr/lib/libz3.so.4", os.path.join(symcc_build_dir, "libz3.so.4"))
    shutil.copy("/libcxx_native_build/lib/libc++.so.1", symcc_build_dir)
    shutil.copy("/libcxx_native_build/lib/libc++abi.so.1", symcc_build_dir)
    # shutil.copy("/mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer/libSymRuntime.so", symcc_build_dir)
    shutil.copy("/mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer/target/release/symcts", symcc_build_dir)
    shutil.copy("/mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer/target/release/print_symcc_trace", symcc_build_dir)


def launch_afl_thread(input_corpus, output_corpus, target_binary,
                      additional_flags):
    """ Simple wrapper for running AFL. """
    afl_thread = threading.Thread(target=afl_fuzzer.run_afl_fuzz,
                                  args=(input_corpus, output_corpus,
                                        target_binary, additional_flags))
    afl_thread.start()
    return afl_thread


def fuzz(input_corpus, output_corpus, target_binary, with_afl=False):
    """
    Launches a master and a secondary instance of AFL, as well as
    the symcts instance.
    """
    target_binary_dir = os.path.dirname(target_binary)
    symcc_workdir = get_symcc_build_dir(target_binary_dir)
    target_binary_name = os.path.basename(target_binary)
    symcc_target_binary = os.path.join(symcc_workdir, target_binary_name)
    vanilla_target_binary = os.path.join('/out/vanilla/', target_binary_name)
    cmplog_target_binary  = os.path.join('/out/cmplog/', target_binary_name)

    fuzzer = os.environ["FUZZER"]

    os.environ['AFL_DISABLE_TRIM'] = '1'

    if "afl" in fuzzer:
        os.environ["AFL_SKIP_CPUFREQ"] = "1"
        os.environ["AFL_NO_AFFINITY"] = "1"
        os.environ["AFL_NO_UI"] = "1"
        os.environ["AFL_MAP_SIZE"] = "256000"
        os.environ["AFL_DRIVER_DONT_DEFER"] = "1"
        os.environ["ASAN_OPTIONS"] = ":detect_leaks=0:abort_on_error=1:symbolize=0"

        flag_cmplog = ["-c", cmplog_target_binary]
        sync_flag_master = ["-F", "/findings/symcts/corpus"] if "symcts" else []

        # Start a master and secondary instance of AFL.
        # We need both because of the way SymCC works.
        print('[run_fuzzer] Running %s' % fuzzer)
        afl_fuzzer.prepare_fuzz_environment(input_corpus)

        launch_afl_thread(input_corpus, output_corpus, target_binary,
                          flag_cmplog + ['-M', 'afl-main'] + sync_flag_master)
        time.sleep(2)
        launch_afl_thread(input_corpus, output_corpus, target_binary,
                          flag_cmplog + ['-S', 'havoc'])
        time.sleep(2)

    if "symcts" in fuzzer:
        symcts_bin = "/out/symcts/symcts"
        if "afl" in fuzzer:
            symcts_bin = "/out/symcts/symcts-from_other"

    cmd = [
        symcts_bin,
        '-i', input_corpus,
        '-s', output_corpus,
        '-n', 'symcts',
        '--'
    ]


    print(os.environ)
    print("TARGET: ", target_binary)

    if "symqemu" in fuzzer:
        cmd += ["/out/symqemu-x86_64", vanilla_target_binary, "@@"]
    else:
        cmd += [symcc_target_binary, "@@"]

    # Start an instance of SyMCTS.
    # We need to ensure it uses the symbolic version of libc++.
    print('Starting the SyMCTS binary')
    new_environ = os.environ.copy()
    new_environ['LD_LIBRARY_PATH'] = symcc_workdir
    new_environ['SYMCTS_INHERIT_STDERR'] = '1'
    new_environ['SYMCTS_INHERIT_STDOUT'] = '1'

    print("############ RUNNING: ", " ".join(cmd))
    with subprocess.Popen(cmd, env=new_environ):
        pass

    # cmd = ['/out/.cargo/bin/cargo', 'run', '--release']
    # cmd += features
    # cmd += ['--bin', 'symcts', '--']
    # cmd += ['-n', 'symcts']
    # cmd += ['-i', input_corpus]
    # cmd += ['-s', output_corpus]
    # cmd += ['--', symcc_target_binary, '@@']
    # print(" ".join(cmd))

    # with subprocess.Popen(cmd, env=new_environ, cwd='/out/mctsse/implementation/libfuzzer_stb_image_symcts/fuzzer/'):
    #     pass
