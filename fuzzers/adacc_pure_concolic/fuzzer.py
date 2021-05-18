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
"""
    Uses a pure-concolic mode of SymCC. We call this
    adacc simply because non-trivial modificaitons has been made
    to SymCC in order to make it to work for pure concolic execution.
"""

import os
import shutil
import subprocess

from fuzzers import utils


def build():
    """
        Builds a version of the benchmark suited for pure
        concolic execution
    """
    # Set flags to ensure compilation with SymCC
    os.environ['CC'] = "/symcc/build/symcc"
    os.environ['CXX'] = "/symcc/build/sym++"
    os.environ['CXXFLAGS'] = os.environ['CXXFLAGS'].replace("-stlib=libc++", "")
    os.environ['FUZZER_LIB'] = '/libfuzzer-harness.o'

    # This instructs SymCC to apply compilation for pure-concolic
    # execution (as opposed to a hybrid of concolic + fuzzing.
    os.environ['SYMCC_PC'] = "1"

    # Use the libc++ library compiles with symbolic instrumentation.
    os.environ['SYMCC_LIBCXX_PATH'] = "/libcxx_native_build"
    # Instructs SymCC to consider no symbolic inputs at runtime. This is needed
    # if, for example, some tests are run during compilation of the benchmark.
    os.environ['SYMCC_NO_SYMBOLIC_INPUT'] = "1"

    # Build benchmark
    utils.build_benchmark()

    # Copy over a bunch of the artifacts
    build_directory = os.environ["OUT"]
    shutil.copy(
        "/symcc/build//SymRuntime-prefix/src/SymRuntime-build/libSymRuntime.so",
        build_directory)
    shutil.copy("/z3/lib/libz3.so.4.8.7.0",
                os.path.join(build_directory, "libz3.so.4.8"))
    shutil.copy("/symcc/util/min-concolic-exec.sh", build_directory)
    shutil.copy("/libcxx_native_build/lib/libc++.so.1.0", build_directory)
    shutil.copy("/libcxx_native_build/lib/libc++.so.1", build_directory)
    shutil.copy("/libcxx_native_build/lib/libc++abi.so.1.0", build_directory)
    shutil.copy("/libcxx_native_build/lib/libc++abi.so.1", build_directory)


def fuzz(input_corpus, output_corpus, target_binary):
    """Runs a pure concolic analysis"""

    # Ensure we have a seed
    os.mkdir("wdir-1")
    with open(os.path.join(input_corpus, "symcc-seed1"), "w+") as init_seed:
        init_seed.write("A" * 100)

    os.environ["THE_OUT_DIR"] = output_corpus

    cmd = []
    cmd.append("./min-concolic-exec.sh")
    cmd.append("-i")
    cmd.append(input_corpus)
    cmd.append("-a")
    cmd.append("./wdir-1")
    cmd.append(target_binary)
    cmd.append("@@")

    subprocess.check_call(cmd)
