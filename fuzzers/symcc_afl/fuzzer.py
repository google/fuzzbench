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
''' Uses the SymCC-AFL hybrid from SymCC '''

import os
import time
import shutil
import threading
import subprocess

from fuzzers import utils
from fuzzers.afl import fuzzer as afl_fuzzer


def get_uninstrumented_build_directory(target_directory):
    """Return path to uninstrumented target directory."""
    return os.path.join(target_directory, 'uninstrumented')


def build():
    build_directory = os.environ['OUT']

    # First build with AFL
    afl_fuzzer.build()
    os.environ['FUZZER_LIB'] = '/libAFL.a'

    src = os.getenv('SRC')
    work = os.getenv('WORK')
    with utils.restore_directory(src), utils.restore_directory(work):
        # Restore SRC to its initial state so we can build again without any
        # trouble. For some OSS-Fuzz projects, build_benchmark cannot be run
        # twice in the same directory without this.
        utils.build_benchmark()

    # Copy over AFL artifacts.
    shutil.copy("/afl/afl-fuzz", build_directory)
    shutil.copy("/afl/afl-showmap", build_directory)

    # Now progress to building the SymCC version of the code.
    print("Building the benchmark with AFL")
    build_directory = os.environ['OUT']
    uninstrumented_build_directory = get_uninstrumented_build_directory(
        build_directory)
    os.mkdir(uninstrumented_build_directory)
    
    print("Building the benchmark with SymCC")
    ## Set flags to ensure compilation with SymCC
    new_env = os.environ.copy()
    new_env['CC'] = "/symcc/build/symcc"
    new_env['CXX'] = "/symcc/build/sym++"
    orig_cxxflags = new_env['CXXFLAGS']
    new_cxxflags = orig_cxxflags.replace("-stlib=libc++", "")
    new_env['CXXFLAGS'] = new_cxxflags
    new_env['SYMCC_REGULAR_LIBCXX'] = "1"
    new_env['SYMCC_NO_SYMBOLIC_INPUT'] = "1"
    new_env['OUT'] = uninstrumented_build_directory
    new_env['FUZZER_LIB'] = '/libfuzzer-harness.o'

    # Build benchmark
    utils.build_benchmark(env=new_env)
    print("Building the benchmark 3")

    # Copy over symcc artifacts.
    shutil.copy(
            "/symcc/build//SymRuntime-prefix/src/SymRuntime-build/libSymRuntime.so",
            build_directory)
    shutil.copy(
           "/z3/lib/libz3.so.4.8.7.0",
           os.path.join(build_directory, "libz3.so.4.8"))

    shutil.copy(
           "/symcc/util/min-concolic-exec.sh",
           build_directory)

    if os.path.isfile("/rust/bin/symcc_fuzzing_helper"):
        print("/rust/bin/symcc_fuzzing_helper is a file")
        shutil.copy("/rust/bin/symcc_fuzzing_helper", build_directory)
    else:
        print("/rust/bin/symcc_fuzzing_helper is not a file")
    if os.path.isfile('/root/.cargo/bin/symcc_fuzzing_helper'):
        print("'/root/.cargo/bin/symcc_fuzzing_helper' is a file")
        shutil.copy('/root/.cargo/bin/symcc_fuzzing_helper', build_directory)
    else:
        print('/root/.cargo/bin/symcc_fuzzing_helper is not a file')

	
def afl_worker(afl_target, input_corpus, output_corpus, is_master):
    afl_fuzz="./afl-fuzz"
    additional_flags = []
    if is_master:
        additional_flags += ["-M", "afl-master"]
    else: 
        additional_flags += ["-S", "afl-secondary"] 

    afl_fuzzer.run_afl_fuzz(input_corpus, 
                            output_corpus, 
                            afl_target, 
                            additional_flags)

def fuzz(input_corpus, output_corpus, target_binary):
    '''
    Launches a master and a secondary instance of AFL, as well as 
    the symcc helper.
    '''

    target_binary_directory = os.path.dirname(target_binary)
    uninstrumented_target_binary_directory = (
        get_uninstrumented_build_directory(target_binary_directory))
    target_binary_name = os.path.basename(target_binary)
    uninstrumented_target_binary = os.path.join(
        uninstrumented_target_binary_directory, target_binary_name)

    afl_fuzzer.prepare_fuzz_environment(input_corpus)

    print('[run_fuzzer] Running AFL for SymQEMU')

    # Start a master
    afl_fuzzer.prepare_fuzz_environment(input_corpus)
    print("Starting master. Target: {target}".format(target=target_binary))
    afl_master_thread = threading.Thread(target=afl_worker, 
                                         args=(target_binary,
                                               input_corpus, 
                                               output_corpus, 
                                               True)) 
    afl_master_thread.start()
    print("Master started.")

    # Give the master time to start
    time.sleep(5)

    # Start a secondary instance. This is due to how
    # the symcc helper script works.
    print("Starting second. Target: {target}".format(target=target_binary))
    afl_secondary_thread = threading.Thread(target=afl_worker, 
                                            args=(target_binary,
                                            input_corpus, 
                                            output_corpus, 
                                            False)) 
    afl_secondary_thread.start()
    print("Second started")

    # Give the secondary instance time to start.
    time.sleep(5)

    # Start an instance of SymCC
    print("Starting the symcc helper")
    cmd = ["./symcc_fuzzing_helper",
                 "-o", output_corpus,
                 "-a", "afl-secondary", 
                 "-n", "symcc", 
                 "--", uninstrumented_target_binary, "@@"]
    subprocess.check_call(cmd)
